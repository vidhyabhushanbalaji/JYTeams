"""Orchestration for the Graph Add section.

Two steps, matching the wizard the frontend shows:

* ``suggest`` — summarise the document, walk the existing tree semantically, rank the places
  it could go, then stage the blob and record an ``add_requests`` row so the user's choice
  can be committed later without re-uploading anything.
* ``place`` — turn the chosen suggestion into rows: optionally create the folder, insert the
  file, then re-describe the affected directories bottom-up so the tree keeps the invariant
  Graph Creation established (every description reflects everything below it).

Ownership is enforced here because the service-role client bypasses row level security.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import PurePosixPath

from fastapi import HTTPException, status

from app.core.config import Settings
from app.graph_add.extract import extract_text
from app.graph_add.labels import (
    NameValidationError,
    child_path,
    folder_label,
    suggested_file_names,
    suggested_folder_names,
    unique_label,
    validate_file_name,
    validate_folder_name,
)
from app.graph_add.navigate import (
    ChildBrief,
    Navigator,
    RankedLocation,
    find_add_locations,
    natural_key,
)
from app.graph_add.repository import AddRepository, Row
from app.graph_add.schemas import PlacementMode
from app.graph_add.storage import ObjectStore, content_hash

logger = logging.getLogger(__name__)

_MIME = "text/markdown"
_MAX_IDENTICAL = 5
_CONTAINS_LIMIT = 6
_DEFAULT_TRAVERSAL = {
    "expanded": 0,
    "visited": 0,
    "degraded": False,
    "budget_exhausted": False,
    "model": "",
}


def _brief(row: Row, contains: Sequence[str] = ()) -> ChildBrief:
    """Project a ``directories`` row onto what the navigator needs."""
    return ChildBrief(
        directory_id=row["id"],
        path=str(row.get("path", "")),
        name=str(row.get("name", "")),
        depth=int(row.get("depth", 0)),
        description=str(row.get("description") or "no description"),
        direct_file_count=int(row.get("direct_file_count", 0)),
        child_directory_count=int(row.get("child_directory_count", 0)),
        contains=tuple(contains),
    )


class _DocumentIndex:
    """In-memory view of one project's tree: lookups plus conflict checks."""

    def __init__(self, directories: Sequence[Row], files: Sequence[Row]) -> None:
        self.directories = list(directories)
        self.files = list(files)
        self.by_id = {row["id"]: row for row in self.directories}
        self._children: dict[str | None, list[Row]] = defaultdict(list)
        for row in self.directories:
            self._children[row.get("parent_id")].append(row)
        self._files_by_directory: dict[str, list[Row]] = defaultdict(list)
        for row in self.files:
            self._files_by_directory[row["directory_id"]].append(row)
        for bucket in (*self._children.values(), *self._files_by_directory.values()):
            bucket.sort(key=lambda row: natural_key(str(row.get("name", ""))))

    def child_rows(self, directory_id: str) -> list[Row]:
        return list(self._children.get(directory_id, []))

    def file_rows(self, directory_id: str) -> list[Row]:
        return list(self._files_by_directory.get(directory_id, []))

    def children_of(self, directory_id: str) -> list[ChildBrief]:
        return [
            _brief(row, self.contains_of(str(row["id"])))
            for row in self._children.get(directory_id, [])
        ]

    def contains_of(self, directory_id: str) -> tuple[str, ...]:
        """A few names of what sits directly inside a folder (subfolders first)."""
        names = [str(row.get("name", "")) for row in self.child_rows(directory_id)]
        names += [
            PurePosixPath(str(row.get("name", ""))).stem for row in self.file_rows(directory_id)
        ]
        seen: set[str] = set()
        picked: list[str] = []
        for name in names:
            key = name.casefold()
            if name and key not in seen:
                seen.add(key)
                picked.append(name)
            if len(picked) == _CONTAINS_LIMIT:
                break
        return tuple(picked)

    def files_of(self, directory_id: str) -> list[tuple[str, str]]:
        return [
            (str(row["name"]), str(row.get("summary") or ""))
            for row in self._files_by_directory.get(directory_id, [])
        ]

    def file_names(self, directory_id: str) -> list[str]:
        return [str(row["name"]) for row in self._files_by_directory.get(directory_id, [])]

    def folder_at(self, path: str) -> Row | None:
        return next((row for row in self.directories if row.get("path") == path), None)

    def file_at(self, path: str) -> Row | None:
        return next((row for row in self.files if row.get("path") == path), None)

    def paths_with_digest(self, digest: str) -> list[str]:
        matches = [
            str(row.get("path", "")) for row in self.files if row.get("content_sha256") == digest
        ]
        return sorted(matches)[:_MAX_IDENTICAL]

    def sibling_names(self, parent_id: str | None) -> list[str]:
        return [str(row.get("name", "")) for row in self._children.get(parent_id, [])]


class GraphAddService:
    """Places a single document into an existing project tree."""

    def __init__(
        self,
        *,
        repository: AddRepository,
        store: ObjectStore,
        navigator: Navigator,
        settings: Settings,
    ) -> None:
        self._repository = repository
        self._store = store
        self._navigator = navigator
        self._settings = settings

    # ---------------------------------------------------------------- suggest

    async def suggest(self, *, owner_id: str, project_id: str, filename: str, data: bytes) -> Row:
        """Summarise the document and return the ranked places it could go."""
        name = self._document_name(filename)
        extracted = extract_text(
            data, filename=name, max_chars=self._settings.summary_max_input_chars
        )
        if not extracted.ok:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"{name!r} cannot be placed: {extracted.reason}.",
            )

        project = await self._require_project(project_id, owner_id)
        index = await self._load_index(project_id)
        root_row = next((row for row in index.directories if row.get("parent_id") is None), None)
        if root_row is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This project has no directory tree to add to yet.",
            )

        summary = await self._summarise(name, extracted.text or "")
        traversal = await find_add_locations(
            root=_brief(root_row, index.contains_of(str(root_row["id"]))),
            children_of=index.children_of,
            files_of=index.files_of,
            summary=summary,
            file_name=name,
            navigator=self._navigator,
        )

        digest = content_hash(data)
        stored = await self._store.put(
            project_id=project["id"], digest=digest, filename=name, data=data
        )
        suggestions = [
            self._suggestion(location, index=index, file_name=name, digest=digest, rank=rank)
            for rank, location in enumerate(traversal.locations, start=1)
        ]
        request = await self._repository.create_add_request(
            {
                "project_id": project["id"],
                "owner_id": owner_id,
                "file_name": name,
                "content_sha256": digest,
                "size_bytes": len(data),
                "mime_type": _MIME,
                "storage_bucket": stored.bucket,
                "storage_path": stored.path,
                "summary": summary,
                "summary_model": self._navigator.model_name,
                "suggestions": suggestions,
                "traversal": traversal.as_dict(self._navigator.model_name),
            }
        )
        return {
            "request_id": request["id"],
            "project_id": project["id"],
            "status": "suggested",
            "expires_at": request.get("expires_at"),
            "file": {
                "name": name,
                "size_bytes": len(data),
                "content_sha256": digest,
                "summary": summary,
            },
            "suggestions": suggestions,
            "traversal": traversal.as_dict(self._navigator.model_name),
        }

    def _suggestion(
        self,
        location: RankedLocation,
        *,
        index: _DocumentIndex,
        file_name: str,
        digest: str,
        rank: int,
    ) -> Row:
        """One suggestion payload, including the rename help the wizard needs."""
        node = location.node
        existing = index.file_names(node.directory_id)
        available = file_name.casefold() not in {name.casefold() for name in existing}
        return {
            "rank": rank,
            "score": round(location.score, 3),
            "directory_id": node.directory_id,
            "path": node.path,
            "name": node.name,
            "depth": node.depth,
            "description": node.description,
            "direct_file_count": node.direct_file_count,
            "child_directory_count": node.child_directory_count,
            "is_leaf": node.is_leaf,
            "reason": location.reason,
            "proposed_new_directory_names": list(location.folder_names),
            "name_available": available,
            "suggested_file_names": (
                [] if available else suggested_file_names(file_name, existing)
            ),
            "identical_content_at": index.paths_with_digest(digest),
        }

    # ------------------------------------------------------------------ place

    async def place(
        self,
        *,
        owner_id: str,
        request_id: str,
        directory_id: str,
        placement: PlacementMode,
        new_directory_name: str | None,
        file_name: str | None,
    ) -> Row:
        """Commit the user's choice: create the folder if asked, then insert the file."""
        placement = _placement_mode(placement)
        request = await self._repository.get_add_request(request_id)
        if request is None or request.get("owner_id") != owner_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Suggestion not found."
            )
        if self._expired(request.get("expires_at")):
            if request.get("status") == "suggested":
                await self._repository.update_add_request(request_id, {"status": "expired"})
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="This suggestion has expired; upload the document again.",
            )
        if request.get("status") != "suggested":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": "This suggestion has already been used.",
                    "status": request.get("status"),
                    "file_id": request.get("placed_file_id"),
                },
            )

        project = await self._require_project(str(request["project_id"]), owner_id)
        project_id = project["id"]
        index = await self._load_index(project_id)

        target = index.by_id.get(directory_id)
        if target is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Directory not found."
            )

        name = self._placement_file_name(file_name or str(request["file_name"]))
        target_path = str(target.get("path", ""))

        # Everything is validated before the first write: a rejection must not leave an
        # empty folder or a half-applied placement behind.
        folder: str | None = None
        if placement is PlacementMode.NEW_DIRECTORY:
            folder = self._folder_name(new_directory_name)
            folder_path = child_path(target_path, folder)
            clash = index.folder_at(folder_path)
            if clash is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "message": f"{target_path or 'the project root'} already has a"
                        f" folder named {folder}.",
                        "conflict": {"directory_path": target_path, "path": folder_path},
                        "suggested_names": suggested_folder_names(
                            folder, index.sibling_names(str(target["id"]))
                        ),
                    },
                )
            file_path = child_path(folder_path, name)
        else:
            file_path = child_path(target_path, name)

        existing = index.file_at(file_path)
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": (
                        f"{target_path or 'the project root'} already has a file named {name}."
                    ),
                    "conflict": {
                        "directory_path": target_path,
                        "path": file_path,
                        "existing_file_id": existing["id"],
                        "identical_content": (
                            existing.get("content_sha256") == request["content_sha256"]
                        ),
                    },
                    "suggested_names": suggested_file_names(
                        name, index.file_names(str(target["id"]))
                    ),
                },
            )

        created: Row | None = None
        if folder is not None:
            created = await self._create_folder(
                project_id=project_id,
                target=target,
                index=index,
                folder=folder,
                file_name=name,
                summary=str(request["summary"]),
            )
            directory_row = created
        else:
            directory_row = target

        inserted = await self._repository.insert_file(
            {
                "project_id": project_id,
                "directory_id": directory_row["id"],
                "name": name,
                "path": file_path,
                "size_bytes": int(request["size_bytes"]),
                "content_sha256": str(request["content_sha256"]),
                "mime_type": str(request.get("mime_type") or _MIME),
                "storage_bucket": str(request["storage_bucket"]),
                "storage_path": str(request["storage_path"]),
                "summary": str(request["summary"]),
                "summary_status": "ok",
                "summary_model": request.get("summary_model"),
            }
        )

        index = await self._load_index(project_id)
        if created is not None:
            await self._recount(str(created["id"]), index)
        refreshed = await self._refresh_from(project_id, target, index)
        await self._repository.update_add_request(
            request_id, {"status": "placed", "placed_file_id": inserted["id"]}
        )
        return {
            "project_id": project_id,
            "request_id": request_id,
            "directory_id": directory_row["id"],
            "directory_path": str(directory_row.get("path", "")),
            "created_directory": created is not None,
            "refreshed_directories": refreshed,
            "file": {
                "id": inserted["id"],
                "name": inserted["name"],
                "path": inserted["path"],
                "directory_id": inserted["directory_id"],
                "size_bytes": int(inserted.get("size_bytes", 0)),
                "summary": inserted.get("summary"),
                "summary_status": inserted.get("summary_status", "ok"),
                "storage_bucket": inserted.get("storage_bucket"),
                "storage_path": inserted.get("storage_path"),
            },
        }

    # ------------------------------------------------------------------- read

    async def get_request(self, request_id: str, owner_id: str) -> Row:
        """Replay a suggestion the user has already seen (also checks expiry)."""
        row = await self._repository.get_add_request(request_id)
        if row is None or row.get("owner_id") != owner_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Suggestion not found."
            )
        return {
            "request_id": row["id"],
            "project_id": row["project_id"],
            "status": row.get("status", "suggested"),
            "expires_at": row.get("expires_at"),
            "file": {
                "name": row["file_name"],
                "size_bytes": int(row.get("size_bytes", 0)),
                "content_sha256": row["content_sha256"],
                "summary": row["summary"],
            },
            "suggestions": row.get("suggestions") or [],
            "traversal": row.get("traversal")
            or {**_DEFAULT_TRAVERSAL, "model": str(row.get("summary_model") or "")},
        }

    # ---------------------------------------------------------------- helpers

    async def _create_folder(
        self,
        *,
        project_id: str,
        target: Row,
        index: _DocumentIndex,
        folder: str,
        file_name: str,
        summary: str,
    ) -> Row:
        """Create the folder the user asked for, described from its one file.

        The caller has already checked that the path is free, so this only writes.
        """
        path = child_path(str(target.get("path", "")), folder)
        description = await self._describe(path, files=[(file_name, summary)], directories=[])
        return await self._repository.insert_directory(
            {
                "project_id": project_id,
                "parent_id": target["id"],
                "name": folder,
                "path": path,
                "ltree_path": self._ltree_path(target, folder, index),
                "depth": int(target.get("depth", 0)) + 1,
                "description": description,
                "description_model": self._navigator.model_name,
                "direct_file_count": 0,
                "child_directory_count": 0,
            }
        )

    async def _describe(
        self,
        path: str,
        *,
        files: Sequence[tuple[str, str]],
        directories: Sequence[tuple[str, str]],
    ) -> str:
        try:
            return await self._navigator.describe_folder(
                path=path, files=files, directories=directories
            )
        except Exception as exc:  # noqa: BLE001 - a missing description must not block
            logger.warning("Could not describe %r: %s", path or "<root>", exc)
            return "Description unavailable."

    async def _refresh_from(self, project_id: str, start: Row, index: _DocumentIndex) -> int:
        """Re-describe ``start`` and its ancestors, deepest first."""
        refreshed = 0
        current = index.by_id.get(str(start["id"])) or start
        for row in [current, *self._ancestors(current, index)]:
            directory_id = str(row["id"])
            file_pairs = [
                (str(item["name"]), str(item.get("summary") or ""))
                for item in index.file_rows(directory_id)
            ]
            directory_pairs = [
                (str(item["name"]), str(item.get("description") or "no description"))
                for item in index.child_rows(directory_id)
            ]
            try:
                text = await self._navigator.describe_folder(
                    path=str(row.get("path", "")),
                    files=file_pairs,
                    directories=directory_pairs,
                )
            except Exception as exc:  # noqa: BLE001 - keep refreshing the rest
                logger.warning(
                    "Could not refresh the description of %r: %s",
                    row.get("path") or "<root>",
                    exc,
                )
                continue

            counts = {
                "direct_file_count": len(file_pairs),
                "child_directory_count": len(directory_pairs),
            }
            await self._repository.update_directory(
                directory_id,
                {
                    "description": text,
                    "description_model": self._navigator.model_name,
                    **counts,
                },
            )
            row.update(counts)
            row["description"] = text
            refreshed += 1
            if not row.get("path"):
                await self._repository.update_project(project_id, {"description": text})
        return refreshed

    async def _recount(self, directory_id: str, index: _DocumentIndex) -> None:
        """Fix the child counts of a folder whose description is already current."""
        await self._repository.update_directory(
            directory_id,
            {
                "direct_file_count": len(index.file_rows(directory_id)),
                "child_directory_count": len(index.child_rows(directory_id)),
            },
        )

    @staticmethod
    def _ancestors(start: Row, index: _DocumentIndex) -> list[Row]:
        """Parents of ``start``, nearest first (cycle-safe)."""
        chain: list[Row] = []
        seen = {str(start["id"])}
        parent_id = start.get("parent_id")
        while parent_id is not None and str(parent_id) not in seen:
            row = index.by_id.get(str(parent_id))
            if row is None:
                break
            chain.append(row)
            seen.add(str(parent_id))
            parent_id = row.get("parent_id")
        return chain

    @staticmethod
    def _ltree_path(target: Row, folder: str, index: _DocumentIndex) -> str:
        """Derive a sibling-unique ltree path for a folder about to be created."""
        base = folder_label(folder)
        used: set[str] = set()
        for row in index.child_rows(str(target["id"])):
            label = str(row.get("ltree_path") or "").rsplit(".", 1)[-1]
            if label:
                used.add(label)
        label = unique_label(base, used)
        parent = str(target.get("ltree_path") or "")
        return f"{parent}.{label}" if parent else label

    @staticmethod
    def _folder_name(raw: str | None) -> str:
        try:
            return validate_folder_name(raw or "")
        except NameValidationError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    @staticmethod
    def _placement_file_name(raw: str) -> str:
        try:
            return validate_file_name(PurePosixPath(raw.replace("\\", "/")).name)
        except NameValidationError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    @staticmethod
    def _document_name(filename: str) -> str:
        raw = PurePosixPath((filename or "").replace("\\", "/")).name
        if not raw.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The upload is missing a file name.",
            )
        try:
            return validate_file_name(raw)
        except NameValidationError as exc:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=str(exc)
            ) from exc

    async def _summarise(self, name: str, text: str) -> str:
        try:
            return await self._navigator.summarise_file(name=name, text=text)
        except Exception as exc:  # noqa: BLE001 - surfaced as a retryable 502
            logger.warning("Could not summarise %r: %s", name, exc)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="The document could not be summarised; try again.",
            ) from exc

    async def _require_project(self, project_id: str, owner_id: str) -> Row:
        project = await self._repository.get_project(project_id)
        if project is None or project.get("owner_id") != owner_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
        return project

    async def _load_index(self, project_id: str) -> _DocumentIndex:
        directories = await self._repository.list_directories(project_id)
        files = await self._repository.list_files(project_id)
        return _DocumentIndex(directories, files)

    @staticmethod
    def _expired(value: object) -> bool:
        moment = _parse_time(value)
        return moment is not None and moment <= datetime.now(UTC)


def _placement_mode(value: PlacementMode | str) -> PlacementMode:
    """Accept a placement as an enum member or its string value."""
    try:
        return PlacementMode(value)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"unknown placement {value!r}; use 'direct' or 'new_directory'",
        ) from exc


def _parse_time(value: object) -> datetime | None:
    """Parse a PostgREST timestamp (or a datetime) into an aware datetime."""
    if isinstance(value, datetime):
        moment = value
    elif isinstance(value, str) and value:
        try:
            moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    return moment if moment.tzinfo else moment.replace(tzinfo=UTC)
