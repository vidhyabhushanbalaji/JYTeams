"""In-memory collaborators so the section can be tested without Supabase, Storage or a model."""

from __future__ import annotations

import itertools
import re
from typing import Any

from app.core.text import Query
from app.graph_ai_search.search import DocumentBrief, DocumentScore, FolderBrief, FolderScore

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

    def seed_file(self, project_id: str, *, directory_id: str, name: str, body: str = "") -> Row:
        """Add one file row, keeping its text where :class:`FakeBlobStore` can find it."""
        directory = self.directories[directory_id]
        path = f"{directory['path']}/{name}" if directory["path"] else name
        row: Row = {
            "id": self._next("file"),
            "project_id": project_id,
            "directory_id": directory_id,
            "name": name,
            "path": path,
            "size_bytes": len(body),
            "content_sha256": f"sha-{name}",
            "mime_type": "text/markdown",
            "storage_bucket": "test-bucket",
            "storage_path": f"{project_id}/{name}",
            "body": body,
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
            "description_model": "local",
            "direct_file_count": 0,
            "child_directory_count": 0,
        }
        self.directories[row["id"]] = row
        return row

    # ----------------------------------------------------------------- reads

    async def get_project(self, project_id: str) -> Row | None:
        project = self.projects.get(project_id)
        return dict(project) if project else None

    async def list_directories(self, project_id: str) -> list[Row]:
        return [dict(row) for row in self.directories.values() if row["project_id"] == project_id]

    async def list_files(self, project_id: str) -> list[Row]:
        return [dict(row) for row in self.files.values() if row["project_id"] == project_id]


class FakeBlobStore:
    """Stand-in for Supabase Storage: objects in a dict, with read tracking."""

    def __init__(self, objects: dict[str, bytes] | None = None) -> None:
        self.objects = dict(objects or {})
        self.reads: list[str] = []
        self.fail_paths: set[str] = set()

    @classmethod
    def from_repository(cls, repository: InMemorySearchRepository) -> FakeBlobStore:
        """Serve each seeded row's text from its ``storage_path``."""
        return cls(
            {
                str(row["storage_path"]): str(row.get("body", "")).encode("utf-8")
                for row in repository.files.values()
            }
        )

    async def get(self, *, bucket: str, path: str) -> bytes:
        self.reads.append(path)
        if path in self.fail_paths:
            raise RuntimeError(f"cannot read {path}")
        return self.objects.get(path, b"")


class ScriptedScorer:
    """Scorer with scripted verdicts, keyed by folder path and by document name.

    The real scorer is tested separately (``test_scoring.py``); this one lets a walk test pin
    exactly which branch opens and which file logs, without depending on its wording.
    """

    version = "scripted"

    def __init__(
        self,
        *,
        folders: dict[str, float] | None = None,
        documents: dict[str, float] | None = None,
        matched: dict[str, tuple[str, ...]] | None = None,
    ) -> None:
        self.folders = folders or {}
        self.documents = documents or {}
        self.matched = matched or {}
        self.folder_calls: list[str] = []
        self.document_calls: list[str] = []

    def score_folder(self, query: Query, folder: FolderBrief) -> FolderScore:
        self.folder_calls.append(folder.path)
        score = self.folders.get(folder.path, 0.0)
        return FolderScore(score=score, matched=self.matched.get(folder.path, ()))

    def score_document(self, query: Query, document: DocumentBrief, body: str) -> DocumentScore:
        self.document_calls.append(document.name)
        score = self.documents.get(document.name, 0.0)
        return DocumentScore(score=score, matched=self.matched.get(document.name, ()))
