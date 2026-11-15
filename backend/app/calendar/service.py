"""Orchestration for the Calendar section.

Two calendars, one service:

* **personal** — the caller's merged view: their own events, the events of every project they are
  in, and the deadlines of the tickets assigned to *them*.
* **project** — that project's events plus every ticket deadline in it.

Deadlines are never stored here. They are read through
:mod:`app.tickets.public` on every request, so a ticket edited in the tickets screen moves on the
calendar immediately, and a completed ticket drops off it.

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

logger = logging.getLogger(__name__)

EVENT = "event"
DEADLINE = "deadline"


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


class CalendarService:
    """Events and ticket deadlines, per project and per person."""

    def __init__(
        self, *, repository: CalendarRepository, access: ProjectAccess, deadlines: DeadlineSource
    ) -> None:
        self._repository = repository
        self._access = access
        self._deadlines = deadlines

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

        row = await self._repository.insert_event(
            {
                "project_id": project_id,
                "member_id": member_id,
                "title": title[:200],
                "notes": (payload.notes or "")[:2_000],
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
        if row.get("project_id"):
            await self._access.require(str(row["project_id"]), member_id)

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
            fields["notes"] = (payload.notes or "")[:2_000]
        if "starts_at" in supplied and payload.starts_at is not None:
            fields["starts_at"] = payload.starts_at.isoformat()
        if "ends_at" in supplied:
            fields["ends_at"] = payload.ends_at.isoformat() if payload.ends_at else None
        if "all_day" in supplied and payload.all_day is not None:
            fields["all_day"] = payload.all_day

        if not fields:
            ids = [str(row["project_id"])] if row.get("project_id") else []
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

    # --------------------------------------------------------------- internals

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
