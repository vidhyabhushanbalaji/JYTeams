"""In-memory collaborators so the section can be tested without Supabase or Gemini."""

from __future__ import annotations

import itertools
import re
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import Any

from app.graph_add.navigate import (
    CandidateContext,
    ChildBrief,
    Judgement,
    RankedCandidate,
)
from app.graph_add.storage import StoredObject

Row = dict[str, Any]


class InMemoryAddRepository:
    """Minimal PostgREST stand-in: rows live in dicts, ids are sequential."""

    def __init__(self) -> None:
        self.projects: dict[str, Row] = {}
        self.directories: dict[str, Row] = {}
        self.files: dict[str, Row] = {}
        self.requests: dict[str, Row] = {}
        self._ids = itertools.count(1)

    def _next(self, prefix: str) -> str:
        return f"{prefix}-{next(self._ids)}"

    # -------------------------------------------------------------- seeding

    def seed_project(self, *, owner_id: str = "user-1", name: str = "Docs") -> Row:
        """Create a project and its root directory (path ``""``, like the real schema)."""
        project: Row = {
            "id": self._next("project"),
            "owner_id": owner_id,
            "name": name,
            "description": None,
            "root_directory_id": None,
        }
        self.projects[project["id"]] = project
        root = self._add_directory(
            project["id"],
            parent_id=None,
            name="",
            path="",
            ltree_path=None,
            depth=0,
            description="The project root.",
        )
        project["root_directory_id"] = root["id"]
        return project

    def seed_directory(
        self, project_id: str, *, parent_id: str, name: str, description: str = ""
    ) -> Row:
        parent = self.directories[parent_id]
        path = f"{parent['path']}/{name}" if parent["path"] else name
        label = re.sub(r"[^a-z0-9_]+", "_", name.lower()).strip("_") or "x"
        ltree = f"{parent['ltree_path']}.{label}" if parent.get("ltree_path") else label
        return self._add_directory(
            project_id,
            parent_id=parent_id,
            name=name,
            path=path,
            ltree_path=ltree,
            depth=int(parent["depth"]) + 1,
            description=description,
        )

    def seed_file(
        self,
        project_id: str,
        *,
        directory_id: str,
        name: str,
        summary: str = "",
        content_sha256: str = "seeded-digest",
    ) -> Row:
        directory = self.directories[directory_id]
        path = f"{directory['path']}/{name}" if directory["path"] else name
        row: Row = {
            "id": self._next("file"),
            "project_id": project_id,
            "directory_id": directory_id,
            "name": name,
            "path": path,
            "size_bytes": 10,
            "content_sha256": content_sha256,
            "mime_type": "text/markdown",
            "storage_bucket": "test-bucket",
            "storage_path": f"{project_id}/{content_sha256}.md",
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
        *,
        parent_id: str | None,
        name: str,
        path: str,
        ltree_path: str | None,
        depth: int,
        description: str | None,
    ) -> Row:
        row: Row = {
            "id": self._next("directory"),
            "project_id": project_id,
            "parent_id": parent_id,
            "name": name,
            "path": path,
            "ltree_path": ltree_path,
            "depth": depth,
            "description": description,
            "description_model": "mock",
            "direct_file_count": 0,
            "child_directory_count": 0,
        }
        self.directories[row["id"]] = row
        if parent_id is not None:
            parent = self.directories[parent_id]
            parent["child_directory_count"] = int(parent.get("child_directory_count", 0)) + 1
        return row

    # ----------------------------------------------------------- repository

    async def get_project(self, project_id: str) -> Row | None:
        row = self.projects.get(project_id)
        return dict(row) if row else None

    async def update_project(self, project_id: str, fields: Row) -> Row:
        self.projects[project_id].update(fields)
        return dict(self.projects[project_id])

    async def list_directories(self, project_id: str) -> list[Row]:
        return [dict(row) for row in self.directories.values() if row["project_id"] == project_id]

    async def list_files(self, project_id: str) -> list[Row]:
        return [dict(row) for row in self.files.values() if row["project_id"] == project_id]

    async def insert_directory(self, row: Row) -> Row:
        record = {**row, "id": self._next("directory")}
        self.directories[record["id"]] = record
        parent_id = record.get("parent_id")
        if parent_id is not None and parent_id in self.directories:
            parent = self.directories[parent_id]
            parent["child_directory_count"] = int(parent.get("child_directory_count", 0)) + 1
        return dict(record)

    async def insert_file(self, row: Row) -> Row:
        record = {**row, "id": self._next("file")}
        self.files[record["id"]] = record
        return dict(record)

    async def update_directory(self, directory_id: str, fields: Row) -> Row:
        self.directories[directory_id].update(fields)
        return dict(self.directories[directory_id])

    async def create_add_request(self, row: Row) -> Row:
        record: Row = {
            "id": self._next("request"),
            "status": "suggested",
            "placed_file_id": None,
            "created_at": datetime.now(UTC).isoformat(),
            "expires_at": (datetime.now(UTC) + timedelta(hours=24)).isoformat(),
            **row,
        }
        self.requests[record["id"]] = record
        return dict(record)

    async def get_add_request(self, request_id: str) -> Row | None:
        row = self.requests.get(request_id)
        return dict(row) if row else None

    async def update_add_request(self, request_id: str, fields: Row) -> Row:
        self.requests[request_id].update(fields)
        return dict(self.requests[request_id])


class InMemoryObjectStore:
    """Records what would have been uploaded to Supabase Storage."""

    bucket = "test-bucket"

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    async def put(
        self, *, project_id: str, digest: str, filename: str, data: bytes
    ) -> StoredObject:
        key = f"{project_id}/{digest}.md"
        self.objects.setdefault(key, data)
        return StoredObject(bucket=self.bucket, path=key)


class ScriptedNavigator:
    """Navigator with scripted answers, so tests pin the traversal exactly."""

    model_name = "scripted"

    def __init__(
        self,
        *,
        matches: dict[str, list[tuple[str, float]]] | None = None,
        ranking: list[str] | None = None,
        folder_names: dict[str, list[str]] | None = None,
        description: str | None = None,
        fail_judging: bool = False,
        fail_summarising: bool = False,
    ) -> None:
        self.matches = matches or {}
        self.ranking = ranking
        self.folder_names = folder_names or {}
        self.description = description
        self.fail_judging = fail_judging
        self.fail_summarising = fail_summarising
        self.calls: list[tuple[str, str]] = []

    async def summarise_file(self, *, name: str, text: str) -> str:
        self.calls.append(("summarise", name))
        if self.fail_summarising:
            raise RuntimeError("summariser unavailable")
        return f"Summary of {name}."

    async def judge_children(
        self,
        *,
        file_name: str,
        summary: str,
        path: str,
        children: Sequence[ChildBrief],
    ) -> Sequence[Judgement]:
        self.calls.append(("judge", path))
        if self.fail_judging:
            raise RuntimeError("navigator unavailable")
        by_name = {child.name: child for child in children}
        judged: list[Judgement] = []
        for name, relevance in self.matches.get(path, []):
            child = by_name.get(name)
            if child is None:
                continue
            judged.append(
                Judgement(
                    directory_id=child.directory_id,
                    relevance=relevance,
                    reason=f"Because of {name}.",
                )
            )
        return judged

    async def rank(
        self,
        *,
        file_name: str,
        summary: str,
        candidates: Sequence[CandidateContext],
    ) -> Sequence[RankedCandidate]:
        self.calls.append(("rank", ""))
        order = self.ranking or [candidate.node.name for candidate in candidates]
        by_name = {candidate.node.name: candidate for candidate in candidates}
        ranked: list[RankedCandidate] = []
        for position, name in enumerate(order):
            candidate = by_name.get(name)
            if candidate is None:
                continue
            ranked.append(
                RankedCandidate(
                    directory_id=candidate.node.directory_id,
                    score=round(1.0 - position * 0.1, 2),
                    reason=f"Ranked {name}.",
                    folder_names=tuple(self.folder_names.get(name, [])),
                )
            )
        return ranked

    async def describe_folder(
        self,
        *,
        path: str,
        files: Sequence[tuple[str, str]],
        directories: Sequence[tuple[str, str]],
    ) -> str:
        self.calls.append(("describe", path))
        if self.description is not None:
            return self.description
        label = path or "the project root"
        names = ", ".join(name for name, _ in files) or "nothing"
        folders = ", ".join(name for name, _ in directories) or "nothing"
        return f"{label} holds files: {names}; subfolders: {folders}."
