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
    summary: str | None = None
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
