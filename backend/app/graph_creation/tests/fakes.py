"""In-memory collaborators so the section can be tested without Supabase."""

from __future__ import annotations

import itertools
from typing import Any

from app.graph_creation.describe import Description, MockDescriber
from app.graph_creation.storage import StorageError, StoredObject

Row = dict[str, Any]


class InMemoryGraphRepository:
    """Minimal PostgREST stand-in: rows live in dicts, ids are sequential."""

    def __init__(self) -> None:
        self.projects: dict[str, Row] = {}
        self.directories: dict[str, Row] = {}
        self.files: dict[str, Row] = {}
        self.jobs: dict[str, Row] = {}
        self._ids = itertools.count(1)

    def _next(self, prefix: str) -> str:
        return f"{prefix}-{next(self._ids)}"

    async def create_project(self, *, owner_id: str, name: str) -> Row:
        row: Row = {
            "id": self._next("project"),
            "owner_id": owner_id,
            "name": name,
            "description": None,
            "root_directory_id": None,
        }
        self.projects[row["id"]] = row
        return dict(row)

    async def update_project(self, project_id: str, fields: Row) -> Row:
        self.projects[project_id].update(fields)
        return dict(self.projects[project_id])

    async def get_project(self, project_id: str) -> Row | None:
        row = self.projects.get(project_id)
        return dict(row) if row else None

    async def list_projects(self, owner_id: str) -> list[Row]:
        return [dict(row) for row in self.projects.values() if row["owner_id"] == owner_id]

    async def create_job(
        self, *, project_id: str, owner_id: str, mode: str, total_files: int
    ) -> Row:
        row: Row = {
            "id": self._next("job"),
            "project_id": project_id,
            "owner_id": owner_id,
            "mode": mode,
            "status": "queued",
            "total_files": total_files,
            "processed_files": 0,
            "failed_files": 0,
            "error": None,
            "finished_at": None,
        }
        self.jobs[row["id"]] = row
        return dict(row)

    async def update_job(self, job_id: str, fields: Row) -> Row:
        self.jobs[job_id].update(fields)
        return dict(self.jobs[job_id])

    async def get_job(self, job_id: str) -> Row | None:
        row = self.jobs.get(job_id)
        return dict(row) if row else None

    async def insert_directories(self, rows: list[Row]) -> list[Row]:
        inserted = []
        for row in rows:
            record = {**row, "id": self._next("directory")}
            self.directories[record["id"]] = record
            inserted.append(dict(record))
        return inserted

    async def insert_files(self, rows: list[Row]) -> list[Row]:
        inserted = []
        for row in rows:
            record = {**row, "id": self._next("file")}
            self.files[record["id"]] = record
            inserted.append(dict(record))
        return inserted

    async def update_file(self, file_id: str, fields: Row) -> Row:
        self.files[file_id].update(fields)
        return dict(self.files[file_id])

    async def get_file(self, file_id: str) -> Row | None:
        row = self.files.get(file_id)
        return dict(row) if row else None

    async def update_directory(self, directory_id: str, fields: Row) -> Row:
        self.directories[directory_id].update(fields)
        return dict(self.directories[directory_id])

    async def get_directory(self, directory_id: str) -> Row | None:
        row = self.directories.get(directory_id)
        return dict(row) if row else None

    async def list_directories(self, project_id: str) -> list[Row]:
        return [dict(row) for row in self.directories.values() if row["project_id"] == project_id]

    async def list_files(self, project_id: str) -> list[Row]:
        return [dict(row) for row in self.files.values() if row["project_id"] == project_id]


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

    async def get(self, *, bucket: str, path: str) -> bytes:
        try:
            return self.objects[path]
        except KeyError as exc:
            raise StorageError(f"missing object {path}") from exc


class RecordingDescriber(MockDescriber):
    """Mock describer that records the order it was called in."""

    def __init__(self) -> None:
        super().__init__()
        self.calls: list[tuple[str, str]] = []

    async def describe_directory(self, *, path: str, files: Any, directories: Any) -> Description:
        self.calls.append(("directory", path))
        return await super().describe_directory(path=path, files=files, directories=directories)
