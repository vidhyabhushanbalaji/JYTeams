"""Orchestration for the Graph Creation section.

Flow: validate the upload → build and prune the tree → describe every directory bottom-up (from
the text of the files it holds and the descriptions of its children) → store the blobs → persist
rows level by level.

There is no per-file summarisation: one directory costs one model call, so a 50-file, 15-folder
upload costs 15 calls instead of 65. A file row still records `summary_status='skipped'`, because
the tree stores documents without describing them individually.

Descriptions are produced before anything is written, so a failed run never leaves a
half-described tree behind; only the job row records the failure.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import PurePosixPath

from fastapi import HTTPException, status

from app.core.access import ProjectAccess
from app.core.activity import DOCUMENT_SAVED, FILES_UPLOADED, NOOP, ActivityLog
from app.core.config import Settings
from app.core.text import clip_description
from app.graph_creation.describe import Describer, trim_for_prompt
from app.graph_creation.extract import extract_text
from app.graph_creation.repository import GraphRepository, Row
from app.graph_creation.schemas import UploadMode
from app.graph_creation.storage import ObjectStore, StoredObject, content_hash
from app.graph_creation.tree import (
    DirectoryNode,
    FileEntry,
    UploadValidationError,
    build_tree,
    by_depth,
    natural_key,
    postorder,
)

logger = logging.getLogger(__name__)

_PROGRESS_MIN_INTERVAL = 1.0
_STORAGE_CONCURRENCY = 4
#: Extensions the viewer offers to edit. Everything else is read-only, because an upload is
#: markdown and nothing else.
_EDITABLE_SUFFIXES = frozenset({".md", ".markdown", ".mdx"})
_BACKGROUND_TASKS: set[asyncio.Task] = set()


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _failure_message(failed: int, detail: str | None) -> str | None:
    """One-line reason stored on a partial job so the cause is visible."""
    if not failed:
        return None
    message = f"{failed} item(s) failed"
    if detail:
        message += f"; first: {detail[:300]}"
    return message


@dataclass
class PreparedUpload:
    """A validated upload, ready to run in the background."""

    project: Row
    job: Row
    tree: DirectoryNode
    mode: UploadMode
    owner_id: str


class GraphCreationService:
    """Builds a directory tree and the descriptions that make it navigable."""

    def __init__(
        self,
        *,
        repository: GraphRepository,
        store: ObjectStore,
        describer: Describer,
        settings: Settings,
        access: ProjectAccess | None = None,
        activity: ActivityLog = NOOP,
    ) -> None:
        self._repository = repository
        self._store = store
        self._describer = describer
        self._settings = settings
        #: Wired by the router in the app. ``None`` keeps the pre-sharing owner check, which is
        #: what the section's unit tests rely on; membership is covered by its own tests.
        self._access = access
        self._activity = activity

    # ------------------------------------------------------------------ submit

    async def prepare(
        self,
        *,
        owner_id: str,
        mode: UploadMode,
        entries: list[FileEntry],
        name: str | None = None,
        project_id: str | None = None,
    ) -> PreparedUpload:
        """Validate the upload and create the project/job rows."""
        try:
            tree = build_tree(
                entries,
                max_depth=self._settings.max_directory_depth,
                max_files=self._settings.max_upload_files,
            )
        except UploadValidationError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

        if mode is UploadMode.ADD:
            if not project_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="project_id is required when mode=add.",
                )
            project = await self._require_project(project_id, owner_id)
            await self._assert_no_path_conflicts(project_id, tree)
        else:
            project = await self._repository.create_project(
                owner_id=owner_id, name=(name or "").strip() or "Untitled project"
            )
            # The creator is the project's first member, and its owner.
            await self._repository.add_project_member(
                project_id=project["id"], member_id=owner_id, role="owner", added_by=owner_id
            )

        job = await self._repository.create_job(
            project_id=project["id"],
            owner_id=owner_id,
            mode=mode.value,
            total_files=tree.total_files,
        )
        return PreparedUpload(project=project, job=job, tree=tree, mode=mode, owner_id=owner_id)

    def schedule(self, prepared: PreparedUpload) -> None:
        """Run the job in the background (single-process worker, see README)."""
        task = asyncio.create_task(self.run_job(prepared))
        _BACKGROUND_TASKS.add(task)
        task.add_done_callback(_BACKGROUND_TASKS.discard)

    async def run_job(self, prepared: PreparedUpload) -> None:
        """Describe the folders and persist. Never raises: failures land on the job row."""
        job_id = prepared.job["id"]
        try:
            await self._repository.update_job(job_id, {"status": "summarising"})
            descriptions, models, failures = await self._describe_tree(prepared)
            error = _failure_message(len(failures), failures[0] if failures else None)

            await self._repository.update_job(job_id, {"status": "persisting"})
            await self._persist(prepared, descriptions, models)

            await self._repository.update_job(
                job_id,
                {
                    "status": "partial" if failures else "ok",
                    "processed_files": prepared.tree.total_files,
                    "failed_files": len(failures),
                    "error": error,
                    "finished_at": _now(),
                },
            )
            await self._record_upload(prepared, failed=len(failures) > 0)
        except Exception as exc:  # noqa: BLE001 - recorded on the job row
            logger.exception("Graph creation job %s failed", job_id)
            try:
                await self._repository.update_job(
                    job_id,
                    {"status": "failed", "error": str(exc)[:1000], "finished_at": _now()},
                )
            except Exception:  # noqa: BLE001 - nothing else we can do
                logger.exception("Could not record failure for job %s", job_id)

    async def _record_upload(self, prepared: PreparedUpload, *, failed: bool) -> None:
        """Tell the activity feed an upload landed. Never raises: the job row is the truth."""
        try:
            await self._activity.record(
                project_id=prepared.project["id"],
                member_id=prepared.owner_id,
                kind=FILES_UPLOADED,
                detail={
                    "mode": prepared.mode.value,
                    "project_name": str(prepared.project.get("name") or ""),
                    "files": prepared.tree.total_files,
                    "directories": sum(len(level) for level in by_depth(prepared.tree).values()),
                    "status": "partial" if failed else "ok",
                },
            )
        except Exception:  # noqa: BLE001 - an audit row must not fail the job
            logger.warning("Could not record the upload event for %s", prepared.project["id"])

    # ---------------------------------------------------------------- describe

    async def _describe_tree(
        self, prepared: PreparedUpload
    ) -> tuple[dict[str, str], dict[str, str], list[str]]:
        """Describe every directory bottom-up, one level at a time.

        A folder is only described once its children are, because its prompt carries their
        descriptions. Folders on the same level are independent, so they run concurrently up to
        ``SUMMARY_CONCURRENCY``: the tree is still produced bottom-up, but a project no longer
        pays a full model round-trip per folder in series.

        A folder that fails stores no description (``None``) and is reported on the job; it does
        not stop its siblings, and its parent is still described.
        """
        tree = prepared.tree
        job_id = prepared.job["id"]
        texts = self._file_texts(tree)
        descriptions: dict[str, str] = {}
        models: dict[str, str] = {}
        failures: list[str] = []
        concurrency = max(1, int(self._settings.summary_concurrency))
        semaphore = asyncio.Semaphore(concurrency)
        lock = asyncio.Lock()
        processed = 0
        reported_at = 0.0

        async def report_progress() -> None:
            nonlocal reported_at
            now = time.monotonic()
            if now - reported_at < _PROGRESS_MIN_INTERVAL:
                return
            reported_at = now
            await self._repository.update_job(
                job_id, {"processed_files": min(processed, tree.total_files)}
            )

        async def describe(node: DirectoryNode) -> None:
            nonlocal processed
            async with semaphore:
                file_pairs = trim_for_prompt(
                    [(entry.name, texts[entry.path]) for entry in node.files],
                    per_file=self._settings.description_file_head_chars,
                    total=self._settings.description_max_input_chars,
                )
                directory_pairs = [
                    (child.name, descriptions.get(child.path) or "no description")
                    for child in node.directories
                ]
                started = time.monotonic()
                try:
                    result = await self._describer.describe_directory(
                        path=node.path, files=file_pairs, directories=directory_pairs
                    )
                except Exception as exc:  # noqa: BLE001 - one folder must not sink the job
                    logger.warning("Could not describe %r: %s", node.path or "<root>", exc)
                    failures.append(
                        f"{node.path or '<root>'}: {type(exc).__name__}: {str(exc)[:300]}"
                    )
                else:
                    descriptions[node.path] = clip_description(
                        result.text, self._settings.description_max_chars
                    )
                    if result.model:
                        models[node.path] = result.model
                    logger.info(
                        "Described %r with %s in %.0f ms",
                        node.path or "<root>",
                        result.model or "?",
                        (time.monotonic() - started) * 1000,
                    )
                async with lock:
                    processed += node.direct_file_count
                    await report_progress()

        for level in reversed(list(by_depth(tree))):
            await asyncio.gather(*(describe(node) for node in level))

        # Always leave the job at its final count, even if the last update was throttled.
        reported_at = 0.0
        await report_progress()
        return descriptions, models, failures

    def _file_texts(self, tree: DirectoryNode) -> dict[str, str]:
        """Decode every uploaded file once, capped for prompt use."""
        limit = self._settings.description_file_head_chars
        return {
            entry.path: self._prompt_text(entry.data, filename=entry.name, limit=limit)
            for entry in _iter_files(tree)
        }

    @staticmethod
    def _prompt_text(data: bytes, *, filename: str, limit: int) -> str:
        """File text for a description prompt, or a note explaining why there is none."""
        extracted = extract_text(data, filename=filename, max_chars=limit)
        if extracted.ok:
            return extracted.text or ""
        return f"(not included: {extracted.reason})"

    async def _stored_text(self, row: Row, cache: dict[str, str]) -> str:
        """Text of an already-stored file, needed when re-describing a folder after an add."""
        key = str(row.get("storage_path") or "")
        if key in cache:
            return cache[key]
        if not key:
            text = "(not included: no stored object)"
        else:
            try:
                data = await self._store.get(
                    bucket=str(row.get("storage_bucket") or self._store.bucket), path=key
                )
                text = self._prompt_text(
                    data,
                    filename=str(row.get("name") or ""),
                    limit=self._settings.description_file_head_chars,
                )
            except Exception as exc:  # noqa: BLE001 - a stale description beats a dead job
                logger.warning("Could not read %r for a description: %s", key, exc)
                text = "(not included: unreadable)"
        cache[key] = text
        return text

    # ---------------------------------------------------------------- persist

    async def _persist(
        self,
        prepared: PreparedUpload,
        descriptions: dict[str, str],
        models: dict[str, str],
    ) -> None:
        stored = await self._store_objects(prepared)
        if prepared.mode is UploadMode.ADD:
            await self._persist_add(prepared, descriptions, models, stored)
        else:
            await self._persist_new(prepared, descriptions, models, stored)

    async def _store_objects(self, prepared: PreparedUpload) -> dict[str, StoredObject]:
        project_id = prepared.project["id"]
        semaphore = asyncio.Semaphore(_STORAGE_CONCURRENCY)
        stored: dict[str, StoredObject] = {}

        async def put(entry: FileEntry) -> None:
            async with semaphore:
                stored[entry.path] = await self._store.put(
                    project_id=project_id,
                    digest=content_hash(entry.data),
                    filename=entry.name,
                    data=entry.data,
                )

        await asyncio.gather(*(put(entry) for entry in _iter_files(prepared.tree)))
        return stored

    async def _persist_new(
        self,
        prepared: PreparedUpload,
        descriptions: dict[str, str],
        models: dict[str, str],
        stored: dict[str, StoredObject],
    ) -> None:
        project_id = prepared.project["id"]
        path_to_id: dict[str, str] = {}

        for level in by_depth(prepared.tree):
            rows = [
                self._directory_row(
                    project_id,
                    node,
                    None if node.parent is None else path_to_id[node.parent.path],
                    descriptions,
                    models,
                )
                for node in level
            ]
            for row in await self._repository.insert_directories(rows):
                path_to_id[row["path"]] = row["id"]

        await self._insert_files(project_id, prepared.tree, path_to_id, stored)
        await self._repository.update_project(
            project_id,
            {
                "root_directory_id": path_to_id.get(""),
                "description": descriptions.get(""),
            },
        )

    async def _persist_add(
        self,
        prepared: PreparedUpload,
        descriptions: dict[str, str],
        models: dict[str, str],
        stored: dict[str, StoredObject],
    ) -> None:
        """Merge the uploaded tree into an existing project, then refresh ancestors."""
        project_id = prepared.project["id"]
        existing = await self._repository.list_directories(project_id)
        path_to_id = {row["path"]: row["id"] for row in existing}
        if "" not in path_to_id:
            raise RuntimeError("project has no root directory")

        merged: set[str] = set()
        for level in by_depth(prepared.tree):
            rows = []
            for node in level:
                if node.path == "":
                    continue  # the upload's root merges into the project root
                if node.path in path_to_id:
                    merged.add(node.path)
                    continue
                parent_id = path_to_id[node.parent.path]
                rows.append(self._directory_row(project_id, node, parent_id, descriptions, models))
            if rows:
                for row in await self._repository.insert_directories(rows):
                    path_to_id[row["path"]] = row["id"]

        await self._insert_files(project_id, prepared.tree, path_to_id, stored)
        await self._refresh_ancestors(prepared, merged)

    async def _insert_files(
        self,
        project_id: str,
        tree: DirectoryNode,
        path_to_id: dict[str, str],
        stored: dict[str, StoredObject],
    ) -> None:
        rows: list[Row] = []
        for node in postorder(tree):
            directory_id = path_to_id[node.path]
            for entry in node.files:
                stored_object = stored[entry.path]
                rows.append(
                    {
                        "project_id": project_id,
                        "directory_id": directory_id,
                        "name": entry.name,
                        "path": entry.path,
                        "size_bytes": entry.size,
                        "content_sha256": content_hash(entry.data),
                        "mime_type": "text/markdown",
                        "storage_bucket": stored_object.bucket,
                        "storage_path": stored_object.path,
                        # Documents are not summarised any more; the folder describes them.
                        # 'skipped' is the existing vocabulary for "stored, not described".
                        "summary": None,
                        "summary_status": "skipped",
                        "summary_model": None,
                    }
                )
        if rows:
            await self._repository.insert_files(rows)

    async def _refresh_ancestors(self, prepared: PreparedUpload, merged: set[str]) -> None:
        """Re-describe the directories a new subtree changed (deepest first)."""
        project_id = prepared.project["id"]
        affected: set[str] = set()
        for node in _iter_dirs(prepared.tree):
            if node.path == "":
                continue
            if node.path in merged:
                affected.add(node.path)
            for ancestor in node.ancestors():
                affected.add(ancestor.path)

        directories = await self._repository.list_directories(project_id)
        files = await self._repository.list_files(project_id)
        by_path = {row["path"]: row for row in directories}
        child_dirs: dict[str | None, list[Row]] = defaultdict(list)
        for row in directories:
            child_dirs[row.get("parent_id")].append(row)
        child_files: dict[str, list[Row]] = defaultdict(list)
        for row in files:
            child_files[row["directory_id"]].append(row)

        def depth(path: str) -> int:
            row = by_path.get(path)
            return int(row["depth"]) if row else 0

        texts = self._file_texts(prepared.tree)
        fetched: dict[str, str] = {}
        for path in sorted(affected, key=depth, reverse=True):
            row = by_path.get(path)
            if row is None:
                continue
            entries: list[tuple[str, str]] = []
            for item in child_files.get(row["id"], []):
                file_text = texts.get(str(item["path"]))
                if file_text is None:
                    file_text = await self._stored_text(item, fetched)
                entries.append((str(item["name"]), file_text))
            file_pairs = trim_for_prompt(
                entries,
                per_file=self._settings.description_file_head_chars,
                total=self._settings.description_max_input_chars,
            )
            directory_pairs = [
                (d["name"], d.get("description") or "no description")
                for d in child_dirs.get(row["id"], [])
            ]
            try:
                result = await self._describer.describe_directory(
                    path=path, files=file_pairs, directories=directory_pairs
                )
            except Exception as exc:  # noqa: BLE001 - keep the rest of the refresh
                logger.warning("Could not refresh description for %r: %s", path or "<root>", exc)
                continue

            text = clip_description(result.text, self._settings.description_max_chars)
            counts = {
                "direct_file_count": len(file_pairs),
                "child_directory_count": len(directory_pairs),
            }
            await self._repository.update_directory(
                row["id"],
                {
                    "description": text,
                    "description_model": result.model,
                    **counts,
                },
            )
            row.update(counts)
            row["description"] = text
            if path == "":
                await self._repository.update_project(project_id, {"description": text})

    # ------------------------------------------------------------------- read

    async def list_projects(self, owner_id: str) -> list[Row]:
        """Every project the caller can see: the ones they created and the ones shared with them.

        ``owner_id`` is the caller's member id; ``role`` on each row says which of the two it is.
        """
        if self._access is None:
            rows = await self._repository.list_projects(owner_id)
        else:
            rows = await self._repository.list_projects_by_ids(
                await self._access.project_ids(owner_id)
            )
        return [self._with_role(row, owner_id) for row in rows]

    async def get_project(self, project_id: str, owner_id: str) -> Row:
        return self._with_role(await self._require_project(project_id, owner_id), owner_id)

    async def get_job(self, job_id: str, owner_id: str) -> Row:
        job = await self._repository.get_job(job_id)
        if job is None or job.get("owner_id") != owner_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")
        return job

    async def get_tree(
        self, project_id: str, owner_id: str, *, max_depth: int | None = None
    ) -> Row:
        project = await self._require_project(project_id, owner_id)
        directories = await self._repository.list_directories(project_id)
        files = await self._repository.list_files(project_id)
        return {
            "project": project,
            "tree": self._assemble_tree(directories, files, max_depth=max_depth),
        }

    async def get_directory(self, directory_id: str, owner_id: str) -> Row:
        directory = await self._repository.get_directory(directory_id)
        if directory is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Directory not found."
            )
        project_id = directory["project_id"]
        await self._require_project(project_id, owner_id)

        directories = await self._repository.list_directories(project_id)
        files = await self._repository.list_files(project_id)
        children = [row for row in directories if row.get("parent_id") == directory_id]
        return {
            "directory": self._directory_summary(directory),
            "files": sorted(
                (self._file_out(row) for row in files if row["directory_id"] == directory_id),
                key=_by_name,
            ),
            "directories": sorted(
                (self._directory_summary(row) for row in children),
                key=_by_name,
            ),
        }

    # --------------------------------------------------------------- documents

    async def get_file_content(self, file_id: str, owner_id: str) -> Row:
        """One document's stored markdown, plus whether the viewer may edit it here."""
        row = await self._require_file(file_id, owner_id)
        bucket = str(row.get("storage_bucket") or self._store.bucket)
        path = str(row.get("storage_path") or "")
        if not path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="This document has no stored file to read.",
            )
        try:
            data = await self._store.get(bucket=bucket, path=path)
        except Exception as exc:  # noqa: BLE001 - one clear error instead of a stack trace
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Could not read this document from storage: {exc}",
            ) from exc

        text = data.decode("utf-8-sig", errors="replace")
        limit = self._settings.file_edit_max_chars
        truncated = len(text) > limit
        return {
            "id": row["id"],
            "name": str(row.get("name", "")),
            "path": str(row.get("path", "")),
            "size_bytes": int(row.get("size_bytes") or len(data)),
            "content_sha256": str(row.get("content_sha256") or content_hash(data)),
            "text": text[:limit] if truncated else text,
            "editable": self._is_editable(row) and not truncated,
            "truncated": truncated,
        }

    async def save_file_content(
        self,
        file_id: str,
        owner_id: str,
        *,
        text: str,
        expected_sha256: str | None = None,
    ) -> Row:
        """Store a new body under its own digest and repoint the row.

        Blobs are content-addressed and may be shared, so the old object is never overwritten —
        editing one path cannot corrupt another document that happens to hold the same bytes.
        No model is called: the folder descriptions refresh on the next add or placement.
        """
        row = await self._require_file(file_id, owner_id)
        if expected_sha256 and expected_sha256 != row.get("content_sha256"):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This document changed since you opened it. Close it and open it again.",
            )
        if not self._is_editable(row):
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Only markdown documents can be edited here.",
            )

        data = text.encode("utf-8")
        if len(data) > self._settings.max_file_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail=(
                    f"This document is {len(data)} bytes; the limit is "
                    f"{self._settings.max_file_bytes}."
                ),
            )

        digest = content_hash(data)
        stored = await self._store.put(
            project_id=str(row["project_id"]),
            digest=digest,
            filename=str(row.get("name", "")),
            data=data,
        )
        updated = await self._repository.update_file(
            file_id,
            {
                "size_bytes": len(data),
                "content_sha256": digest,
                "storage_bucket": stored.bucket,
                "storage_path": stored.path,
            },
        )
        try:
            await self._activity.record(
                project_id=str(row["project_id"]),
                member_id=owner_id,
                kind=DOCUMENT_SAVED,
                detail={
                    "file_id": str(row["id"]),
                    "file_name": str(row.get("name") or ""),
                    "path": str(row.get("path") or ""),
                },
            )
        except Exception:  # noqa: BLE001 - the save already happened
            logger.warning("Could not record the save event for %s", row["id"])
        return {**self._file_out(updated), "content_sha256": digest}

    # ----------------------------------------------------------------- helpers

    async def _require_project(self, project_id: str, owner_id: str) -> Row:
        """One project, with the caller's access checked (404 for either miss).

        ``owner_id`` is the caller's member id. With an access guard the check is project
        membership, so a shared project is reachable; without one it is the original owner
        comparison, which is what the section's unit tests set up.
        """
        project = await self._repository.get_project(project_id)
        if project is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
        if self._access is not None:
            await self._access.require(project_id, owner_id)
        elif project.get("owner_id") != owner_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
        return project

    @staticmethod
    def _with_role(project: Row, member_id: str) -> Row:
        """Add the caller's role, which the API returns so the UI can badge a shared project."""
        role = "owner" if project.get("owner_id") == member_id else "member"
        return {**project, "role": role}

    async def _require_file(self, file_id: str, owner_id: str) -> Row:
        """One file row, with its project's ownership checked (404 for either miss)."""
        row = await self._repository.get_file(file_id)
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
        await self._require_project(str(row["project_id"]), owner_id)
        return row

    @staticmethod
    def _is_editable(row: Row) -> bool:
        suffix = PurePosixPath(str(row.get("name") or "")).suffix.lower()
        return suffix in _EDITABLE_SUFFIXES

    async def _assert_no_path_conflicts(self, project_id: str, tree: DirectoryNode) -> None:
        existing = await self._repository.list_files(project_id)
        existing_paths = {row["path"] for row in existing}
        conflicts = sorted({entry.path for entry in _iter_files(tree)} & existing_paths)
        if conflicts:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": "Some uploaded paths already exist in this project.",
                    "conflicts": conflicts[:20],
                    "conflict_count": len(conflicts),
                },
            )

    def _directory_row(
        self,
        project_id: str,
        node: DirectoryNode,
        parent_id: str | None,
        descriptions: dict[str, str],
        models: dict[str, str],
    ) -> Row:
        description = descriptions.get(node.path)
        return {
            "project_id": project_id,
            "parent_id": parent_id,
            "name": node.name,
            "path": node.path,
            "ltree_path": node.ltree_path or None,
            "depth": node.depth,
            "description": description,
            "description_model": models.get(node.path) if description else None,
            "direct_file_count": node.direct_file_count,
            "child_directory_count": node.child_directory_count,
        }

    def _assemble_tree(
        self,
        directories: list[Row],
        files: list[Row],
        *,
        max_depth: int | None,
    ) -> Row:
        by_parent: dict[str | None, list[Row]] = defaultdict(list)
        for row in directories:
            by_parent[row.get("parent_id")].append(row)
        files_by_directory: dict[str, list[Row]] = defaultdict(list)
        for row in files:
            files_by_directory[row["directory_id"]].append(row)

        root = next((row for row in directories if row.get("parent_id") is None), None)
        if root is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Project tree not found."
            )

        def build(row: Row, level: int) -> Row:
            children: list[Row] = []
            if max_depth is None or level + 1 < max_depth:
                children = [
                    build(child, level + 1)
                    for child in sorted(by_parent.get(row["id"], []), key=_by_name)
                ]
            return {
                **self._directory_summary(row),
                "files": [
                    self._file_out(item)
                    for item in sorted(files_by_directory.get(row["id"], []), key=_by_name)
                ],
                "directories": children,
            }

        return build(root, 0)

    @staticmethod
    def _directory_summary(row: Row) -> Row:
        return {
            "id": row["id"],
            "name": row.get("name", ""),
            "path": row.get("path", ""),
            "depth": int(row.get("depth", 0)),
            "description": row.get("description"),
            "direct_file_count": int(row.get("direct_file_count", 0)),
            "child_directory_count": int(row.get("child_directory_count", 0)),
        }

    @staticmethod
    def _file_out(row: Row) -> Row:
        return {
            "id": row["id"],
            "name": row["name"],
            "path": row["path"],
            "size_bytes": int(row.get("size_bytes", 0)),
            "summary": row.get("summary"),
            "summary_status": row.get("summary_status", "pending"),
            "storage_bucket": row.get("storage_bucket"),
            "storage_path": row.get("storage_path"),
        }


def _by_name(row: Row) -> tuple:
    return natural_key(str(row.get("name", "")))


def _iter_files(node: DirectoryNode):
    """Every uploaded file, in post-order."""
    for directory in postorder(node):
        yield from directory.files


def _iter_dirs(node: DirectoryNode):
    """Every directory, children first."""
    yield from postorder(node)
