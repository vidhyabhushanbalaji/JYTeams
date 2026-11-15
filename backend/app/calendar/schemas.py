"""Request and response models for the Calendar section.

One response shape carries both kinds of thing a calendar shows — an event somebody added and a
ticket's deadline — so the desktop app sorts and renders one list, not two.
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field, model_validator

#: How far one request may look, so a calendar cannot be asked for a decade in one call.
MAX_RANGE_DAYS = 400


class PersonOut(BaseModel):
    """A member, by name (the only identity this build has)."""

    id: str
    display_name: str


class EventMentionOut(BaseModel):
    """A reference stored with an event's notes (resolved when the event was written)."""

    kind: str
    id: str
    label: str
    #: The document's or folder's path; empty for a ticket.
    path: str = ""
    #: The folder a document lives in, so the graph can reveal it directly.
    directory_path: str = ""
    #: The ticket's number, when the mention is a ticket.
    ticket_number: int | None = None


class CalendarItemOut(BaseModel):
    """One thing on a day: an added event, or a ticket's deadline."""

    #: `event` or `deadline`.
    kind: str
    id: str
    title: str
    #: The day the item sits on (a datetime's local date for an event).
    day: date
    project_id: str | None = None
    project_name: str = ""
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    all_day: bool = False
    notes: str = ""
    #: True for an event the caller created; the app only offers edit/delete then.
    editable: bool = False
    created_by: PersonOut | None = None
    #: Set on a deadline so the app can open the ticket.
    ticket_id: str | None = None
    ticket_number: int | None = None
    status: str | None = None
    priority: str | None = None
    assignee: PersonOut | None = None
    #: Documents, folders and tickets the event's notes mention.
    mentions: list[EventMentionOut] = Field(default_factory=list)


class MentionTargetOut(BaseModel):
    """One thing an event's notes may offer after an `@`."""

    kind: str
    id: str
    label: str
    path: str = ""
    directory_path: str = ""
    ticket_number: int | None = None
    #: A short hint (`guide`, `#12 · To do`), shown beside the label.
    detail: str = ""


class CalendarOut(BaseModel):
    """One calendar over a date range."""

    #: `personal` (the caller's merged view) or `project`.
    scope: str
    project_id: str | None = None
    project_name: str = ""
    start: date
    end: date
    items: list[CalendarItemOut] = Field(default_factory=list)


class EventIn(BaseModel):
    """A new event.

    ``project_id`` decides the scope: set means a project event (every member sees it), null
    means a personal event (only its creator sees it).
    """

    project_id: str | None = None
    title: str = Field(min_length=1, max_length=200)
    notes: str = Field(default="", max_length=2_000)
    starts_at: datetime
    ends_at: datetime | None = None
    all_day: bool = False

    @model_validator(mode="after")
    def _range_is_ordered(self) -> EventIn:
        if self.ends_at is not None and self.ends_at < self.starts_at:
            raise ValueError("an event cannot end before it starts")
        return self


class EventPatch(BaseModel):
    """A partial edit; only the fields that were sent are applied."""

    title: str | None = Field(default=None, min_length=1, max_length=200)
    notes: str | None = Field(default=None, max_length=2_000)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    all_day: bool | None = None

    def supplied(self) -> set[str]:
        """The fields the client actually sent (so ``null`` can mean "clear the end time")."""
        return set(self.model_fields_set)


class EventOut(BaseModel):
    """One stored event."""

    id: str
    project_id: str | None = None
    project_name: str = ""
    title: str
    notes: str = ""
    starts_at: datetime
    ends_at: datetime | None = None
    all_day: bool = False
    created_by: PersonOut | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    #: The documents, folders and tickets the notes mention (resolved when it was saved).
    mentions: list[EventMentionOut] = Field(default_factory=list)
