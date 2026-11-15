"""Request and response models for the Graph Add section."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class PlacementMode(StrEnum):
    """Where the approved document should land, relative to the chosen directory."""

    DIRECT = "direct"
    """Put the file in the chosen directory itself."""

    NEW_DIRECTORY = "new_directory"
    """Create a new directory under the chosen one and put the file inside it."""


class FileBrief(BaseModel):
    """The uploaded document as the client last saw it."""

    name: str
    size_bytes: int
    content_sha256: str
    #: First ~200 characters of the document — no model wrote it, so it is always faithful.
    preview: str


class Suggestion(BaseModel):
    """One possible home for the document."""

    rank: int
    score: float
    directory_id: str
    path: str
    name: str
    depth: int
    description: str | None = None
    direct_file_count: int
    child_directory_count: int
    is_leaf: bool
    reason: str
    #: The document's own words that the folder matched, so the score is explainable.
    matched_terms: list[str] = Field(default_factory=list)
    proposed_new_directory_names: list[str] = Field(default_factory=list)
    name_available: bool
    suggested_file_names: list[str] = Field(default_factory=list)
    identical_content_at: list[str] = Field(default_factory=list)


class ScanInfo(BaseModel):
    """What the local ranking cost (no model was called)."""

    folders_scored: int
    threshold: float
    scorer_version: str


class SuggestionAccepted(BaseModel):
    """The ranked suggestions for one uploaded document."""

    request_id: str
    project_id: str
    status: str = "suggested"
    expires_at: datetime | None = None
    #: The surrounding context that was allowed to steer the ranking (usually a ticket).
    context: str = ""
    file: FileBrief
    suggestions: list[Suggestion] = Field(default_factory=list)
    scan: ScanInfo


class PlacementIn(BaseModel):
    """The choice the user made in the wizard."""

    request_id: str
    directory_id: str
    placement: PlacementMode = PlacementMode.DIRECT
    new_directory_name: str | None = None
    file_name: str | None = None


class PlacedFileOut(BaseModel):
    """The file row that was written."""

    id: str
    name: str
    path: str
    directory_id: str
    size_bytes: int
    #: Always `skipped`: documents are not summarised, the folder is described instead.
    summary_status: str
    storage_bucket: str | None = None
    storage_path: str | None = None


class PlacementOut(BaseModel):
    """Result of committing a suggestion."""

    project_id: str
    request_id: str
    directory_id: str
    directory_path: str
    created_directory: bool
    #: Folders whose description was refreshed (one model call covered all of them).
    refreshed_directories: int
    file: PlacedFileOut
