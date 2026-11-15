"""Orchestration for the Calendar section.

Two calendars, one service:

* **personal** — the caller's merged view: their own events, the events of every project they are
  in, and the deadlines of the tickets assigned to *them*.
* **project** — that project's events plus every ticket deadline in it.

Deadlines are never stored here. They are read through
:mod:`app.tickets.public` on every request, so a ticket edited in the tickets screen moves on the
calendar immediately, and a completed ticket drops off it.

An event's notes may mention a document, a folder or a ticket, using the same
``@[label](kind:id)`` markers chat writes. They are parsed and validated against the event's
project when the event is written, then stored resolved on the row — so the calendar, chat, and a
ticket's "on the calendar" list all read the same facts.

Items sit on the day they start; a multi-day event appears on its first day.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime, time
from typing import Any, Protocol

from fastapi import HTTPException, status

from app.calendar.repository import CalendarRepository, Row
from app.calendar.schemas import MAX_RANGE_DAYS, EventIn, EventPatch
from app.core.access import ProjectAccess
from app.core.mentions import MAX_MENTIONS, Mention, extract

logger = logging.getLogger(__name__)

EVENT = "event"
DEADLINE = "deadline"

#: The mention kinds an event's notes may point at (an event does not mention another event).
MENTIONABLE_KINDS: tuple[str, ...] = ("file", "directory", "ticket")

#: What one picker query may return.
MAX_TARGETS = 20


class DeadlineSource(Protocol):
    """What the calendar needs from the tickets section (read-only, model-free)."""

    async def list_deadlines(
        self,
        *,
        project_ids: Sequence[str],
        assignee_id: str | None,
        start: date,
        end: date,
    ) -> list[dict[str, Any]]: ...


class MentionCatalogue(Protocol):
    """What the calendar needs from the sections that own documents, folders and tickets."""

    async def search(self, *, project_id: str, query: str, limit: int) -> list[dict[str, Any]]: ...

    async def describe(
        self, *, project_id: str, mentions: Sequence[Mention]
    ) -> dict[tuple[str, str], dict[str, Any]]: ...


def _person(row: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if not row:
        return None
    return {"id": str(row["id"]), "display_name": str(row.get("display_name") or "Member")}


def _as_datetime(value: Any) -> datetime | None:
    """A timezone-aware datetime from a PostgREST timestamp (or a datetime)."""
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if isinstance(value, str) and value:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    return None


def _as_date(value: Any) -> date | None:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str) and value:
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


def _mentions_of(row: Mapping[str, Any]) -> list[dict[str, Any]]:
    """A row's resolved mentions, normalised for the response and for chat's use."""
    mentions: list[dict[str, Any]] = []
    for item in row.get("mentions") or []:
        if not isinstance(item, Mapping):
            continue
        mentions.append(
            {
                "kind": str(item.get("kind") or ""),
                "id": str(item.get("id") or ""),
                "label": str(item.get("label") or "item"),
                "path": str(item.get("path") or ""),
                "directory_path": str(item.get("directory_path") or ""),
                "ticket_number": item.get("ticket_number"),
            }
        )
    return mentions


class CalendarService:
    """Events and ticket deadlines, per project and per person."""

    def __init__(
        self,
        *,
        repository: CalendarRepository,
        access: ProjectAccess,
        deadlines: DeadlineSource,
        catalogue: MentionCatalogue,
    ) -> None:
        self._repository = repository
        self._access = access
        self._deadlines = deadlines
        self._catalogue = catalogue

    # ---------------------------------------------------------------- reading

    async def personal(self, *, member_id: str, start: date, end: date) -> dict[str, Any]:
        """The individual calendar: everything in my projects, plus deadlines assigned to me."""
        first, last = _window(start, end)
        project_ids = await self._access.project_ids(member_id)

        events = await self._repository.list_personal_events(
            member_id=member_id, start=first, end=last
        )
        events += await self._repository.list_project_events(
            project_ids=project_ids, start=first, end=last
        )
        deadlines = await self._deadlines.list_deadlines(
            project_ids=project_ids, assignee_id=member_id, start=start, end=end
        )

        names = await self._project_names(project_ids)
        authors = await self._authors(events, deadlines)
        items = _merge(
            [_event_item(row, member_id, names, authors) for row in events],
            [_deadline_item(row, names, authors) for row in deadlines],
        )
        return {
            "scope": "personal",
            "project_id": None,
            "project_name": "My calendar",
            "start": start,
            "end": end,
            "items": items,
        }

    async def project(
        self, *, member_id: str, project_id: str, start: date, end: date
    ) -> dict[str, Any]:
        """One project's calendar: its events plus every deadline in it."""
        await self._access.require(project_id, member_id)
        first, last = _window(start, end)

        events = await self._repository.list_project_events(
            project_ids=[project_id], start=first, end=last
        )
        deadlines = await self._deadlines.list_deadlines(
            project_ids=[project_id], assignee_id=None, start=start, end=end
        )

        names = await self._project_names([project_id])
        authors = await self._authors(events, deadlines)
        items = _merge(
            [_event_item(row, member_id, names, authors) for row in events],
            [_deadline_item(row, names, authors) for row in deadlines],
        )
        return {
            "scope": "project",
            "project_id": project_id,
            "project_name": names.get(project_id, "Project"),
            "start": start,
            "end": end,
            "items": items,
        }

    # ---------------------------------------------------------------- writing

    async def create_event(self, *, member_id: str, payload: EventIn) -> dict[str, Any]:
        """Add an event: a project one (any member) or a personal one (only me)."""
        title = " ".join((payload.title or "").split())
        if not title:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="an event needs a title"
            )

        project_id = payload.project_id or None
        if project_id:
            await self._access.require(project_id, member_id)

        notes = (payload.notes or "")[:2_000]
        mentions = await self._resolve_notes(project_id, notes)

        row = await self._repository.insert_event(
            {
                "project_id": project_id,
                "member_id": member_id,
                "title": title[:200],
                "notes": notes,
                "mentions": mentions,
                "starts_at": payload.starts_at.isoformat(),
                "ends_at": payload.ends_at.isoformat() if payload.ends_at else None,
                "all_day": payload.all_day,
            }
        )
        names = await self._project_names([project_id] if project_id else [])
        authors = await self._authors([row], [])
        return _event_out(row, names, authors)

    async def update_event(
        self, *, member_id: str, event_id: str, payload: EventPatch
    ) -> dict[str, Any]:
        """Edit an event. Only the person who added it may change it."""
        row = await self._require_event(event_id)
        self._require_creator(row, member_id)
        project_id = str(row["project_id"]) if row.get("project_id") else None
        if project_id:
            await self._access.require(project_id, member_id)

        supplied = payload.supplied()
        fields: dict[str, Any] = {}

        if "title" in supplied and payload.title is not None:
            title = " ".join(payload.title.split())
            if not title:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail="an event needs a title"
                )
            fields["title"] = title[:200]
        if "notes" in supplied:
            notes = (payload.notes or "")[:2_000]
            fields["notes"] = notes
            # The notes changed, so the resolved set must be rebuilt from the new markers.
            fields["mentions"] = await self._resolve_notes(project_id, notes)
        if "starts_at" in supplied and payload.starts_at is not None:
            fields["starts_at"] = payload.starts_at.isoformat()
        if "ends_at" in supplied:
            fields["ends_at"] = payload.ends_at.isoformat() if payload.ends_at else None
        if "all_day" in supplied and payload.all_day is not None:
            fields["all_day"] = payload.all_day

        if not fields:
            ids = [project_id] if project_id else []
            return _event_out(row, await self._project_names(ids), await self._authors([row], []))

        starts = _as_datetime(fields.get("starts_at", row.get("starts_at")))
        ends = _as_datetime(fields.get("ends_at", row.get("ends_at")))
        if starts and ends and ends < starts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="an event cannot end before it starts",
            )

        updated = await self._repository.update_event(event_id, fields)
        ids = [str(updated["project_id"])] if updated.get("project_id") else []
        return _event_out(
            updated, await self._project_names(ids), await self._authors([updated], [])
        )

    async def delete_event(self, *, member_id: str, event_id: str) -> None:
        """Remove an event. Only the person who added it may delete it."""
        row = await self._require_event(event_id)
        self._require_creator(row, member_id)
        await self._repository.delete_event(event_id)

    # --------------------------------------------------------------- mentions

    async def mention_targets(
        self, *, member_id: str, project_id: str, query: str, limit: int = MAX_TARGETS
    ) -> list[dict[str, Any]]:
        """What an event's notes may offer after an `@`: documents, folders and tickets."""
        await self._access.require(project_id, member_id)
        cleaned = " ".join((query or "").split())[:120]
        rows = await self._catalogue.search(
            project_id=project_id, query=cleaned, limit=max(1, min(limit, 50))
        )
        return [
            {
                "kind": str(row.get("kind") or ""),
                "id": str(row.get("id") or ""),
                "label": str(row.get("label") or "item"),
                "path": str(row.get("path") or ""),
                "directory_path": str(row.get("directory_path") or ""),
                "ticket_number": row.get("ticket_number"),
                "detail": str(row.get("detail") or ""),
            }
            for row in rows
        ]

    async def events_mentioning(
        self, *, member_id: str, project_id: str, kind: str, target_id: str
    ) -> list[dict[str, Any]]:
        """Project events whose notes mention one document, folder or ticket.

        This is what a ticket's panel reads to show the meetings it is discussed in; it is a
        plain read of the resolved mentions, so no model is called.
        """
        await self._access.require(project_id, member_id)
        if kind not in MENTIONABLE_KINDS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"an event can mention: {', '.join(MENTIONABLE_KINDS)}",
            )
        rows = await self._repository.list_events_mentioning(
            project_id=project_id, kind=kind, target_id=target_id
        )
        names = await self._project_names([project_id])
        authors = await self._authors(rows, [])
        items = [_event_item(row, member_id, names, authors) for row in rows]
        items.sort(key=lambda item: (item["day"], item["title"].casefold()))
        return items

    # --------------------------------------------------------------- internals

    async def _resolve_notes(self, project_id: str | None, notes: str) -> list[dict[str, Any]]:
        """Parse an event's notes and resolve every mention inside its project.

        A personal event has no project to check a mention against, so markers there stay plain
        text and nothing is stored; a project event refuses a marker that is not part of it.
        """
        mentions = extract(notes)
        if not mentions:
            return []
        if project_id is None:
            return []
        if len(mentions) > MAX_MENTIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"an event's notes may mention at most {MAX_MENTIONS} things",
            )

        found = await self._catalogue.describe(project_id=project_id, mentions=mentions)
        missing = [
            f"{mention.kind}:{mention.id}" for mention in mentions if mention.key not in found
        ]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="these mentions are not part of this project: " + ", ".join(sorted(missing)),
            )
        return [
            {
                "kind": str(found[mention.key].get("kind") or mention.kind),
                "id": str(found[mention.key].get("id") or mention.id),
                "label": str(found[mention.key].get("label") or mention.label),
                "path": str(found[mention.key].get("path") or ""),
                "directory_path": str(found[mention.key].get("directory_path") or ""),
                "ticket_number": found[mention.key].get("ticket_number"),
            }
            for mention in mentions
        ]

    async def _require_event(self, event_id: str) -> Row:
        row = await self._repository.get_event(event_id)
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found.")
        return row

    @staticmethod
    def _require_creator(row: Mapping[str, Any], member_id: str) -> None:
        if str(row.get("member_id") or "") != member_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the person who added this event can change it.",
            )

    async def _project_names(self, project_ids: Sequence[str]) -> dict[str, str]:
        ids = sorted({str(value) for value in project_ids if value})
        if not ids:
            return {}
        rows = await self._repository.list_projects_by_ids(ids)
        return {str(row["id"]): str(row.get("name") or "Project") for row in rows}

    async def _authors(
        self, events: Sequence[Row], deadlines: Sequence[Mapping[str, Any]]
    ) -> dict[str, Mapping[str, Any]]:
        ids = {str(row.get("member_id") or "") for row in events}
        ids |= {str((row.get("assignee") or {}).get("id") or "") for row in deadlines}
        ids -= {""}
        if not ids:
            return {}
        members = await self._repository.list_members_by_ids(sorted(ids))
        return {str(row["id"]): row for row in members}


def _window(start: date, end: date) -> tuple[datetime, datetime]:
    """The datetimes an inclusive date range covers, or 400 when the range is unusable."""
    if end < start:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="the range ends before it starts"
        )
    if (end - start).days > MAX_RANGE_DAYS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"a calendar covers at most {MAX_RANGE_DAYS} days at a time",
        )
    return (
        datetime.combine(start, time.min, tzinfo=UTC),
        datetime.combine(end, time.max, tzinfo=UTC),
    )


def _event_item(
    row: Row,
    member_id: str,
    names: Mapping[str, str],
    authors: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    project_id = str(row["project_id"]) if row.get("project_id") else None
    creator = str(row.get("member_id") or "")
    starts = _as_datetime(row.get("starts_at"))
    return {
        "kind": EVENT,
        "id": str(row["id"]),
        "title": str(row.get("title") or "Event"),
        "day": starts.date() if starts else date.today(),
        "project_id": project_id,
        "project_name": names.get(project_id or "", ""),
        "starts_at": starts,
        "ends_at": _as_datetime(row.get("ends_at")),
        "all_day": bool(row.get("all_day")),
        "notes": str(row.get("notes") or ""),
        "editable": creator == member_id,
        "created_by": _person(authors.get(creator)),
        "ticket_id": None,
        "ticket_number": None,
        "status": None,
        "priority": None,
        "assignee": None,
        "mentions": _mentions_of(row),
    }


def _deadline_item(
    row: Mapping[str, Any],
    names: Mapping[str, str],
    authors: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    project_id = str(row.get("project_id") or "")
    assignee = row.get("assignee") or {}
    assignee_id = str(assignee.get("id") or "")
    return {
        "kind": DEADLINE,
        "id": str(row.get("ticket_id") or ""),
        "title": str(row.get("title") or "Ticket deadline"),
        "day": _as_date(row.get("due_date")) or date.today(),
        "project_id": project_id or None,
        "project_name": names.get(project_id, ""),
        "starts_at": None,
        "ends_at": None,
        "all_day": True,
        "notes": "",
        "editable": False,
        "created_by": None,
        "ticket_id": str(row.get("ticket_id") or ""),
        "ticket_number": row.get("number"),
        "status": row.get("status"),
        "priority": row.get("priority"),
        "assignee": _person(authors.get(assignee_id)),
        "mentions": [],
    }


def _event_out(
    row: Row, names: Mapping[str, str], authors: Mapping[str, Mapping[str, Any]]
) -> dict[str, Any]:
    project_id = str(row["project_id"]) if row.get("project_id") else None
    creator = str(row.get("member_id") or "")
    starts = _as_datetime(row.get("starts_at")) or datetime.now(UTC)
    return {
        "id": str(row["id"]),
        "project_id": project_id,
        "project_name": names.get(project_id or "", ""),
        "title": str(row.get("title") or "Event"),
        "notes": str(row.get("notes") or ""),
        "starts_at": starts,
        "ends_at": _as_datetime(row.get("ends_at")),
        "all_day": bool(row.get("all_day")),
        "created_by": _person(authors.get(creator)),
        "created_at": _as_datetime(row.get("created_at")),
        "updated_at": _as_datetime(row.get("updated_at")),
        "mentions": _mentions_of(row),
    }


def _merge(
    events: Sequence[dict[str, Any]], deadlines: Sequence[dict[str, Any]]
) -> list[dict[str, Any]]:
    """One ordered list: by day, then events (at their time) before that day's deadlines."""
    items = [*events, *deadlines]

    def key(item: Mapping[str, Any]) -> tuple[date, int, float, str]:
        starts = item.get("starts_at")
        order = 1 if item.get("kind") == DEADLINE else 0
        seconds = starts.timestamp() if isinstance(starts, datetime) else 0.0
        return (item["day"], order, seconds, str(item.get("title") or "").casefold())

    items.sort(key=key)
    return items
