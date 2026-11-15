"""Orchestration for the Graph AI Search section.

One read path: validate the query, check the project belongs to the caller, weight the query
against the project's own vocabulary, walk the tree (folder descriptions decide which branches
to open, document bodies decide which files match), then trim the ranked results. No model is
called and nothing is written, so there is no job row and no cleanup.

Documents are read through :class:`app.graph_ai_search.storage.DocumentTextReader`, which caches
by content digest — identical documents share one read, and a repeated search is nearly free.
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from collections.abc import Sequence
from pathlib import PurePosixPath

from fastapi import HTTPException, status

from app.core.access import ProjectAccess
from app.core.config import Settings
from app.core.text import build_query
from app.graph_ai_search.repository import Row, SearchRepository
from app.graph_ai_search.search import (
    DocumentBrief,
    FolderBrief,
    Scorer,
    find_matching_files,
    natural_key,
)
from app.graph_ai_search.storage import DocumentTextReader

logger = logging.getLogger(__name__)

MIN_QUERY_CHARS = 3
MAX_QUERY_CHARS = 500
MAX_CONTEXT_CHARS = 500
MAX_LIMIT = 25
DEFAULT_LIMIT = 8
_CONTAINS_LIMIT = 6


def _folder(row: Row, contains: Sequence[str]) -> FolderBrief:
    """Project a ``directories`` row onto what the walk needs."""
    return FolderBrief(
        directory_id=row["id"],
        path=str(row.get("path", "")),
        name=str(row.get("name", "")),
        depth=int(row.get("depth", 0)),
        description=str(row.get("description") or ""),
        contains=tuple(contains),
        direct_file_count=int(row.get("direct_file_count", 0)),
        child_directory_count=int(row.get("child_directory_count", 0)),
    )


def _document(row: Row, directory_path: str) -> DocumentBrief:
    """Project a ``files`` row onto what the walk needs, including where its bytes live."""
    return DocumentBrief(
        file_id=row["id"],
        name=str(row.get("name", "")),
        path=str(row.get("path", "")),
        directory_id=row["directory_id"],
        directory_path=directory_path,
        storage_bucket=str(row.get("storage_bucket") or ""),
        storage_path=str(row.get("storage_path") or ""),
        content_sha256=str(row.get("content_sha256") or ""),
    )


class ProjectTree:
    """In-memory view of one project's tree, for the walk's lookup callables."""

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

    @property
    def root(self) -> Row | None:
        return next((row for row in self.directories if row.get("parent_id") is None), None)

    def corpus(self) -> list[str]:
        """Every name and description, used to weight rare query terms more heavily."""
        texts = [
            f"{row.get('name', '')} {row.get('description') or ''}" for row in self.directories
        ]
        texts.extend(str(row.get("path", "")) for row in self.files)
        return texts

    def contains_of(self, directory_id: str) -> tuple[str, ...]:
        """A few names of what sits directly inside a folder (subfolders first)."""
        names = [str(row.get("name", "")) for row in self._children.get(directory_id, [])]
        names += [
            PurePosixPath(str(row.get("name", ""))).stem
            for row in self._files_by_directory.get(directory_id, [])
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

    def children_of(self, directory_id: str) -> list[FolderBrief]:
        return [
            _folder(row, self.contains_of(str(row["id"])))
            for row in self._children.get(directory_id, [])
        ]

    def documents_of(self, directory_id: str) -> list[DocumentBrief]:
        parent = self.by_id.get(directory_id)
        parent_path = str(parent.get("path", "")) if parent else ""
        return [
            _document(row, parent_path) for row in self._files_by_directory.get(directory_id, [])
        ]


class GraphSearchService:
    """Answers a query from the tree's descriptions and the documents themselves."""

    def __init__(
        self,
        *,
        repository: SearchRepository,
        reader: DocumentTextReader,
        scorer: Scorer,
        settings: Settings,
        access: ProjectAccess | None = None,
    ) -> None:
        self._repository = repository
        self._reader = reader
        self._scorer = scorer
        self._settings = settings
        #: Wired by the router. ``None`` keeps the pre-sharing owner check for unit tests;
        #: project membership is what the app uses.
        self._access = access

    async def search(
        self,
        *,
        project_id: str,
        owner_id: str,
        query: str,
        limit: int = DEFAULT_LIMIT,
        min_score: float = 0.0,
        max_directories: int | None = None,
        context: str = "",
    ) -> Row:
        """Walk the tree for ``query`` (plus optional context) and return the ranked matches."""
        cleaned = " ".join((query or "").split())
        extra = " ".join((context or "").split())
        self._validate(
            cleaned,
            context=extra,
            limit=limit,
            min_score=min_score,
            max_directories=max_directories,
        )

        started = time.perf_counter()
        project = await self._require_project(project_id, owner_id)
        tree = ProjectTree(
            await self._repository.list_directories(project_id),
            await self._repository.list_files(project_id),
        )
        root_row = tree.root
        if root_row is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This project has no directory tree to search yet.",
            )

        outcome = await find_matching_files(
            root=_folder(root_row, tree.contains_of(str(root_row["id"]))),
            documents_of=tree.documents_of,
            children_of=tree.children_of,
            read_body=self._read_body,
            query=build_query(f"{cleaned} {extra}".strip(), corpus=tree.corpus()),
            scorer=self._scorer,
            total_documents=len(tree.files),
            max_directories=max_directories,
            folder_threshold=self._settings.scoring_folder_threshold,
            max_files_read=self._settings.search_max_files_read,
        )
        duration_ms = int((time.perf_counter() - started) * 1000)

        hits = [
            {
                "file_id": item.document.file_id,
                "name": item.document.name,
                "path": item.document.path,
                "directory_id": item.document.directory_id,
                "directory_path": item.document.directory_path,
                "score": round(item.score, 3),
                "matched_terms": list(item.matched),
                "excerpt": item.excerpt,
            }
            for item in outcome.results
            if item.score >= min_score
        ][:limit]
        directories = [
            {
                "directory_id": item.directory_id,
                "path": item.path,
                "name": item.name,
                "depth": item.depth,
                "score": round(item.score, 3),
                "matched_terms": list(item.matched),
            }
            for item in outcome.directories
        ][:MAX_LIMIT]

        return {
            "query": cleaned,
            "context": extra,
            "project_id": project["id"],
            "results": hits,
            "directories": directories,
            "opened_directories": outcome.opened,
            "traversal": outcome.traversal(duration_ms=duration_ms),
        }

    async def _read_body(self, document: DocumentBrief) -> str:
        """Read one document's text through the digest cache."""
        if not document.storage_path:
            raise ValueError(f"{document.path} has no stored object")
        return await self._reader.read(
            bucket=document.storage_bucket,
            path=document.storage_path,
            digest=document.content_sha256,
        )

    @staticmethod
    def _validate(
        query: str,
        *,
        context: str,
        limit: int,
        min_score: float,
        max_directories: int | None,
    ) -> None:
        if len(query) < MIN_QUERY_CHARS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"a query needs at least {MIN_QUERY_CHARS} characters",
            )
        if len(query) > MAX_QUERY_CHARS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"the query is longer than {MAX_QUERY_CHARS} characters",
            )
        if len(context) > MAX_CONTEXT_CHARS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"the context is longer than {MAX_CONTEXT_CHARS} characters",
            )
        if not 1 <= limit <= MAX_LIMIT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"limit must be between 1 and {MAX_LIMIT}",
            )
        if not 0.0 <= min_score <= 1.0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="min_score must be 0.0-1.0"
            )
        if max_directories is not None and max_directories < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="max_directories must be at least 1 when given",
            )

    async def _require_project(self, project_id: str, owner_id: str) -> Row:
        """One project, with the caller's access checked (404 for either miss).

        ``owner_id`` is the caller's member id. With an access guard the check is project
        membership, so a shared project is searchable; without one it is the original owner
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
