"""Request and response models for the Chat section.

The chat has its own ``AuthorOut`` instead of borrowing the tickets section's ``MemberOut``: a
section may not import another section's internals, and a two-field shape is not worth an
interface.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class AuthorOut(BaseModel):
    """Who wrote a message (a name — the only identity this build has)."""

    id: str
    display_name: str


class MentionOut(BaseModel):
    """A reference that was validated and stored with the message."""

    kind: str
    id: str
    label: str
    #: The document's or folder's path; empty for a ticket.
    path: str = ""
    #: The folder a document lives in, so the graph can reveal it directly.
    directory_path: str = ""
    #: The ticket's number, when the mention is a ticket.
    ticket_number: int | None = None


class ChatMessageOut(BaseModel):
    """One message, as the chat shows it."""

    seq: int
    id: str
    project_id: str
    author: AuthorOut | None = None
    body: str
    mentions: list[MentionOut] = Field(default_factory=list)
    created_at: datetime | None = None
    #: A message the author (or the project owner) removed; the row stays so seq never gaps.
    deleted: bool = False


class ChannelOut(BaseModel):
    """A project's group chat: the project, plus the last thing said in it."""

    project_id: str
    project_name: str
    last_message: ChatMessageOut | None = None
    last_activity_at: datetime | None = None


class MentionTargetOut(BaseModel):
    """One thing the composer may offer after an `@`."""

    kind: str
    id: str
    label: str
    path: str = ""
    directory_path: str = ""
    ticket_number: int | None = None
    #: A short hint (`guide`, `#12 · To do`), shown beside the label.
    detail: str = ""


class MessageIn(BaseModel):
    """A new message.

    Mentions are not a separate field: the composer inserts `@[label](kind:id)` markers into
    ``body``, and the backend parses and validates them. One source of truth means the text a
    reader sees is always the text that was resolved.
    """

    body: str = Field(min_length=1, max_length=4_000)
