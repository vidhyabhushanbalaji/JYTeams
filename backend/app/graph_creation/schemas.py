"""Request and response models for the Graph Creation section."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class UploadMode(StrEnum):
    """What the uploaded directory means."""

    NEW = "new"
    """Build a new project tree (also how a re-upload starts over)."""

    ADD = "add"
    """Append the uploaded directory into an existing project tree."""


class FileOut(BaseModel):
    id: str
    name: str
    path: str
    size_bytes: int
    #: Null for every document: Graph Creation describes folders, not individual files.
    summary: str | None = None
    #: Always `skipped` — "stored, not described" in the existing vocabulary.
    summary_status: str
    storage_bucket: str | None = None
    storage_path: str | None = None


class DirectoryOut(BaseModel):
    id: str
    name: str
    path: str
    depth: int
    description: str | None = None
    direct_file_count: int
    child_directory_count: int
    files: list[FileOut] = Field(default_factory=list)
    directories: list[DirectoryOut] = Field(default_factory=list)


DirectoryOut.model_rebuild()


class ProjectOut(BaseModel):
    id: str
    name: str
    description: str | None = None
    root_directory_id: str | None = None
    created_at: datetime | None = None


class JobOut(BaseModel):
    id: str
    project_id: str
    mode: str
    status: str
    total_files: int
    processed_files: int
    failed_files: int
    error: str | None = None
    created_at: datetime | None = None
    finished_at: datetime | None = None


class UploadAccepted(BaseModel):
    project_id: str
    job_id: str
    mode: UploadMode
    total_files: int


class ProjectTreeOut(BaseModel):
    project: ProjectOut
    tree: DirectoryOut


class DirectoryChildrenOut(BaseModel):
    directory: DirectoryOut
    files: list[FileOut] = Field(default_factory=list)
    directories: list[DirectoryOut] = Field(default_factory=list)


class FileContentOut(BaseModel):
    """One document's stored markdown, ready for the viewer."""

    id: str
    name: str
    path: str
    size_bytes: int
    content_sha256: str
    text: str
    #: Markdown, and short enough to edit here; otherwise the sheet is read-only.
    editable: bool
    #: True when the stored text exceeded FILE_EDIT_MAX_CHARS and ``text`` was cut for display.
    truncated: bool = False


class FileContentIn(BaseModel):
    """A replacement body.

    ``expected_sha256`` is the digest the client read; when it no longer matches, the save is
    refused so a stale window cannot overwrite a newer edit.
    """

    text: str
    expected_sha256: str | None = None


class FileSavedOut(FileOut):
    """The file row after a save, plus the digest the client should quote next time."""

    content_sha256: str
