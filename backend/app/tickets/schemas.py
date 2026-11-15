"""Request and response models for the Tickets section."""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class TicketStatus(StrEnum):
    """The ticket's lifecycle. `done` is what the completion checkbox sets."""

    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"


class Priority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class MemberOut(BaseModel):
    """One person, by name — the only identity this build has."""

    id: str
    display_name: str


class ProjectMemberOut(MemberOut):
    role: str
    added_at: datetime | None = None


class SignInIn(BaseModel):
    """Sign in (or join) with a name. No password, by design."""

    display_name: str = Field(min_length=1, max_length=60)


class ShareIn(BaseModel):
    member_id: str


class TicketFileHit(BaseModel):
    """One document the search found for a ticket."""

    file_id: str
    name: str
    path: str
    directory_id: str
    directory_path: str
    score: float
    matched_terms: list[str] = Field(default_factory=list)
    excerpt: str = ""


class AttachedFileOut(BaseModel):
    """A document deliberately put on the ticket."""

    file_id: str
    name: str
    path: str
    directory_path: str
    size_bytes: int
    added_at: datetime | None = None
    added_by: MemberOut | None = None
    #: `upload` when the ticket's own upload flow placed it, `existing` when it was picked.
    source: str = "existing"


class TicketFilesOut(BaseModel):
    """The ticket's documents: what search suggested, and what the team attached."""

    query: str = ""
    context: str = ""
    suggested: list[TicketFileHit] = Field(default_factory=list)
    attached: list[AttachedFileOut] = Field(default_factory=list)
    #: When the search result was computed (null when it has never run).
    cached_at: datetime | None = None
    #: The stored result no longer matches the ticket/project; a refresh would fix it.
    stale: bool = False
    #: Why there is nothing to suggest (for example a ticket with no description).
    reason: str | None = None


class TicketOut(BaseModel):
    """A ticket as the list shows it."""

    id: str
    project_id: str
    project_name: str = ""
    number: int
    title: str
    description: str = ""
    status: TicketStatus
    priority: Priority
    due_date: date | None = None
    labels: list[str] = Field(default_factory=list)
    assignee: MemberOut | None = None
    reporter: MemberOut | None = None
    completed_at: datetime | None = None
    completed_by: MemberOut | None = None
    attachment_count: int = 0
    comment_count: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None


class CommentOut(BaseModel):
    """One comment on a ticket."""

    id: str
    body: str
    author: MemberOut | None = None
    created_at: datetime | None = None


class TicketDetailOut(TicketOut):
    """A ticket plus its comments and documents."""

    comments: list[CommentOut] = Field(default_factory=list)
    files: TicketFilesOut = Field(default_factory=TicketFilesOut)


class TicketCreateIn(BaseModel):
    """A new ticket. The reporter is the caller; the assignee defaults to them too."""

    project_id: str
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=5_000)
    assignee_id: str | None = None
    priority: Priority = Priority.MEDIUM
    due_date: date | None = None
    labels: list[str] = Field(default_factory=list, max_length=10)


class TicketUpdateIn(BaseModel):
    """A partial update. Only the fields that were sent are applied."""

    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5_000)
    assignee_id: str | None = None
    priority: Priority | None = None
    due_date: date | None = None
    labels: list[str] | None = Field(default=None, max_length=10)

    def supplied(self) -> set[str]:
        """The field names the client actually sent (so ``null`` can mean "clear")."""
        return set(self.model_fields_set)


class TicketStatusIn(BaseModel):
    """Move a ticket, or tick its completion box."""

    status: TicketStatus


class CommentIn(BaseModel):
    """A comment body."""

    body: str = Field(min_length=1, max_length=4_000)


class AttachIn(BaseModel):
    """Attach a document that is already in the project."""

    file_id: str
    #: `upload` for a file the ticket's own wizard just placed, `existing` for a pick.
    source: str = "existing"


class TicketEventOut(BaseModel):
    """One line of the project's changes-and-updates feed."""

    id: str
    kind: str
    detail: dict[str, Any] = Field(default_factory=dict)
    project_id: str
    ticket_id: str | None = None
    ticket_number: int | None = None
    actor: MemberOut | None = None
    created_at: datetime | None = None
