"""In-memory collaborators so the section can be tested without Supabase or Gemini."""

from __future__ import annotations

import itertools
import re
from collections.abc import Sequence
from typing import Any

from app.graph_ai_search.search import (
    DocumentBrief,
    DocumentMatch,
    FileRank,
    FolderBrief,
    FolderMatch,
    FolderVerdicts,
    LoggedFile,
)

Row = dict[str, Any]


class InMemorySearchRepository:
    """Minimal read-only PostgREST stand-in: rows live in dicts."""

    def __init__(self) -> None:
        self.projects: dict[str, Row] = {}
        self.directories: dict[str, Row] = {}
        self.files: dict[str, Row] = {}
        self._ids = itertools.count(1)

    def _next(self, prefix: str) -> str:
        return f"{prefix}-{next(self._ids)}"

    # -------------------------------------------------------------- seeding

    def seed_project(self, *, owner_id: str = "user-1", name: str = "Docs") -> Row:
        """Create a project with a root directory (path ``""``)."""
        project: Row = {
            "id": self._next("project"),
            "owner_id": owner_id,
            "name": name,
            "description": None,
            "root_directory_id": None,
        }
        self.projects[project["id"]] = project
        root = self._add_directory(project["id"], None, "", "", 0, "The project root.")
        project["root_directory_id"] = root["id"]
        return project

    def seed_directory(
        self, project_id: str, *, parent_id: str, name: str, description: str = ""
    ) -> Row:
        parent = self.directories[parent_id]
        path = f"{parent['path']}/{name}" if parent["path"] else name
        row = self._add_directory(
            project_id, parent_id, name, path, int(parent["depth"]) + 1, description
        )
        parent["child_directory_count"] = int(parent.get("child_directory_count", 0)) + 1
        return row

    def seed_file(self, project_id: str, *, directory_id: str, name: str, summary: str = "") -> Row:
        directory = self.directories[directory_id]
        path = f"{directory['path']}/{name}" if directory["path"] else name
        row: Row = {
            "id": self._next("file"),
            "project_id": project_id,
            "directory_id": directory_id,
            "name": name,
            "path": path,
            "size_bytes": 10,
            "content_sha256": f"sha-{name}",
            "mime_type": "text/markdown",
            "storage_bucket": "test-bucket",
            "storage_path": f"{project_id}/{name}",
            "summary": summary,
            "summary_status": "ok",
            "summary_model": "mock",
        }
        self.files[row["id"]] = row
        directory["direct_file_count"] = int(directory.get("direct_file_count", 0)) + 1
        return row

    def _add_directory(
        self,
        project_id: str,
        parent_id: str | None,
        name: str,
        path: str,
        depth: int,
        description: str,
    ) -> Row:
        row: Row = {
            "id": self._next("directory"),
            "project_id": project_id,
            "parent_id": parent_id,
            "name": name,
            "path": path,
            "ltree_path": re.sub(r"[^a-z0-9_]+", "_", path.lower()) or None,
            "depth": depth,
            "description": description,
            "description_model": "mock",
            "direct_file_count": 0,
            "child_directory_count": 0,
        }
        self.directories[row["id"]] = row
        return row

    # ----------------------------------------------------------- repository

    async def get_project(self, project_id: str) -> Row | None:
        row = self.projects.get(project_id)
        return dict(row) if row else None

    async def list_directories(self, project_id: str) -> list[Row]:
        return [dict(row) for row in self.directories.values() if row["project_id"] == project_id]

    async def list_files(self, project_id: str) -> list[Row]:
        return [dict(row) for row in self.files.values() if row["project_id"] == project_id]


class ScriptedSearcher:
    """Searcher with scripted answers, keyed by folder path.

    ``matches`` maps a folder path to the names it should log and the subfolder names it
    should open, so a test can pin the walk exactly::

        {"": {"files": ["README.md"], "folders": ["docs", "guides"]},
         "guides": {"files": ["deployment.md"], "folders": []}}
    """

    model_name = "scripted"

    def __init__(
        self,
        *,
        matches: dict[str, dict[str, list[str]]] | None = None,
        ranking: list[str] | None = None,
        fail_judging: bool = False,
        fail_ranking: bool = False,
    ) -> None:
        self.matches = matches or {}
        self.ranking = ranking
        self.fail_judging = fail_judging
        self.fail_ranking = fail_ranking
        self.calls: list[tuple[str, str]] = []
        self.ranked_batches: list[list[str]] = []

    async def judge(
        self,
        *,
        query: str,
        folder: FolderBrief,
        documents: Sequence[DocumentBrief],
        folders: Sequence[FolderBrief],
    ) -> FolderVerdicts:
        self.calls.append(("judge", folder.path))
        if self.fail_judging:
            raise RuntimeError("searcher unavailable")

        script = self.matches.get(folder.path, {})
        by_file = {item.name: item for item in documents}
        by_folder = {item.name: item for item in folders}

        document_matches = [
            DocumentMatch(
                file_id=by_file[name].file_id,
                relevance=round(max(0.05, 0.9 - index * 0.01), 2),
                reason=f"Scripted file match: {name}.",
            )
            for index, name in enumerate(script.get("files", []))
            if name in by_file
        ]
        folder_matches = [
            FolderMatch(
                directory_id=by_folder[name].directory_id,
                relevance=round(max(0.05, 0.8 - index * 0.01), 2),
                reason=f"Scripted folder match: {name}.",
            )
            for index, name in enumerate(script.get("folders", []))
            if name in by_folder
        ]
        return FolderVerdicts(documents=tuple(document_matches), folders=tuple(folder_matches))

    async def rank(self, *, query: str, documents: Sequence[LoggedFile]) -> Sequence[FileRank]:
        self.calls.append(("rank", query))
        self.ranked_batches.append([item.document.name for item in documents])
        if self.fail_ranking:
            raise RuntimeError("ranking unavailable")

        order = self.ranking or [item.document.name for item in documents]
        by_name = {item.document.name: item for item in documents}
        ranked: list[FileRank] = []
        for position, name in enumerate(order):
            item = by_name.get(name)
            if item is None:
                continue
            ranked.append(
                FileRank(
                    file_id=item.document.file_id,
                    score=round(1.0 - position * 0.1, 2),
                    reason=f"Scripted rank {position + 1}.",
                )
            )
        return ranked
