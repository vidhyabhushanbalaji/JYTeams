"""The public surface of the Calendar section — the only module another section may import.

Chat offers a composer's ``@`` suggestions and validates the mentions a message carries; a
calendar event's notes also use the same markers. Chat needs a project's events as mention
targets, so this module exposes exactly that — read-only, no model call, no write:

* :func:`search_targets` — project events whose title matches what was typed after ``@``.
* :func:`describe_targets` — resolve ``("event", id)`` refs that belong to one project.

Personal events have no project to validate against, so they are never offered or resolved here;
a mention is only meaningful inside a project.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, date, datetime
from typing import Any

from app.calendar.repository import SupabaseCalendarRepository

#: How many suggestions one query returns at most.
TARGET_LIMIT = 20
#: The hard ceiling, so a caller cannot ask for every event in one picker.
MAX_TARGET_LIMIT = 50
#: The pool a picker searches (a project calendar is small; this only guards a runaway import).
MAX_EVENTS = 500

EVENT = "event"

Target = dict[str, Any]
Ref = tuple[str, str]


def event_day(value: Any) -> date | None:
    """The day an event sits on (its start, in UTC) — shared by the calendar's own code too."""
    if isinstance(value, datetime):
        moment = value if value.tzinfo else value.replace(tzinfo=UTC)
        return moment.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str) and value:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            try:
                return date.fromisoformat(value[:10])
            except ValueError:
                return None
        return (parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)).date()
    return None


def _rank(title: str, needle: str) -> int:
    """0 = the title starts with the query, 1 = it contains it, 2 = it does not match."""
    if not needle:
        return 0
    lowered = title.casefold()
    if lowered.startswith(needle):
        return 0
    return 1 if needle in lowered else 3


def _event_target(row: dict[str, Any]) -> Target:
    day = event_day(row.get("starts_at"))
    return {
        "kind": EVENT,
        "id": str(row["id"]),
        "label": str(row.get("title") or "Event"),
        "path": "",
        "directory_path": "",
        "ticket_number": None,
        # A plain ISO day, so the value that chat stores on its row is JSON-safe.
        "event_day": day.isoformat() if day else None,
        "detail": f"{day.isoformat()} · event" if day else "event",
    }


async def search_targets(*, project_id: str, query: str, limit: int = TARGET_LIMIT) -> list[Target]:
    """A project's events that match ``query`` by title, soonest first."""
    repository = SupabaseCalendarRepository()
    rows = await repository.list_project_events_all(project_id=project_id, limit=MAX_EVENTS)

    needle = " ".join((query or "").split()).casefold()
    candidates: list[tuple[int, str, Target]] = []
    for row in rows:
        target = _event_target(row)
        rank = _rank(target["label"], needle)
        if rank < 3:
            candidates.append((rank, str(row.get("starts_at") or ""), target))

    candidates.sort(key=lambda item: (item[0], item[1], item[2]["label"].casefold()))
    return [target for _, _, target in candidates[: max(1, min(limit, MAX_TARGET_LIMIT))]]


async def describe_targets(*, project_id: str, refs: Sequence[Ref]) -> dict[Ref, Target]:
    """Resolve ``("event", id)`` refs that belong to this project (others are absent)."""
    wanted = {ref for ref in refs if ref[0] == EVENT}
    if not wanted:
        return {}

    rows = await SupabaseCalendarRepository().get_events_by_ids([ref[1] for ref in wanted])
    found: dict[Ref, Target] = {}
    for row in rows:
        if str(row.get("project_id") or "") != project_id:
            continue
        key = (EVENT, str(row["id"]))
        if key in wanted:
            found[key] = _event_target(row)
    return found
