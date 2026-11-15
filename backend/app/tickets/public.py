"""The public surface of the Tickets section — the only module another section may import.

Two read-only needs, both model-free and write-free:

* Chat and the calendar need a ticket's number, title and status to label a mention.
* The calendar shows ticket deadlines, read live from ``tickets.due_date`` so a ticket edited in
  the tickets screen moves on the calendar immediately.

Nothing here creates, updates or deletes a ticket, and nothing here calls a model.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from typing import Any

from app.tickets.repository import SupabaseTicketRepository

#: How many suggestions one query returns at most.
TARGET_LIMIT = 20
#: The hard ceiling for one picker query.
MAX_TARGET_LIMIT = 50

TICKET = "ticket"

Target = dict[str, Any]
Ref = tuple[str, str]

_STATUS_LABEL = {"todo": "To do", "in_progress": "In progress", "done": "Done"}


def _status_label(value: str) -> str:
    return _STATUS_LABEL.get(value, value.replace("_", " ").title() or "Ticket")


def _ticket_target(row: dict[str, Any]) -> Target:
    number = int(row.get("number") or 0)
    status = str(row.get("status") or "todo")
    return {
        "kind": TICKET,
        "id": str(row["id"]),
        "label": str(row.get("title") or f"Ticket #{number}"),
        "path": "",
        "directory_path": "",
        "ticket_number": number,
        "detail": f"#{number} · {_status_label(status)}",
    }


def _rank(title: str, number: int, needle: str) -> int:
    if not needle:
        return 0
    lowered = title.casefold()
    if lowered.startswith(needle):
        return 0
    if f"#{number}" == needle or f"#{number}".startswith(needle):
        return 0
    if needle in lowered:
        return 1
    return 3


async def search_targets(*, project_id: str, query: str, limit: int = TARGET_LIMIT) -> list[Target]:
    """Tickets of one project that match ``query`` by title or ``#number``."""
    repository = SupabaseTicketRepository()
    rows = await repository.list_tickets(project_ids=[project_id], limit=500)
    needle = " ".join((query or "").split()).casefold().removeprefix("tickets ")

    candidates: list[tuple[int, int, Target]] = []
    for row in rows:
        target = _ticket_target(row)
        rank = _rank(target["label"], int(target["ticket_number"] or 0), needle)
        if rank < 3:
            candidates.append((rank, int(target["ticket_number"] or 0), target))

    candidates.sort(key=lambda item: (item[0], item[1]))
    return [target for _, _, target in candidates[: max(1, min(limit, MAX_TARGET_LIMIT))]]


async def describe_targets(*, project_id: str, refs: Sequence[Ref]) -> dict[Ref, Target]:
    """Resolve ``("ticket", id)`` refs that belong to this project (others are absent)."""
    wanted = {ref for ref in refs if ref[0] == TICKET}
    if not wanted:
        return {}
    rows = await SupabaseTicketRepository().get_tickets_by_ids([ref[1] for ref in wanted])
    found: dict[Ref, Target] = {}
    for row in rows:
        if str(row.get("project_id") or "") != project_id:
            continue
        key = (TICKET, str(row["id"]))
        if key in wanted:
            found[key] = _ticket_target(row)
    return found


def _iso_date(value: Any) -> str | None:
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str) and value:
        return value[:10]
    return None


async def list_deadlines(
    *,
    project_ids: Sequence[str],
    assignee_id: str | None = None,
    start: date | None = None,
    end: date | None = None,
    include_done: bool = False,
) -> list[dict[str, Any]]:
    """Tickets with a due date: the deadlines a calendar shows.

    ``assignee_id`` narrows to one person's tickets (the individual calendar); without it every
    deadline of the given projects is returned (a project calendar).
    """
    ids = [str(value) for value in project_ids if value]
    repository = SupabaseTicketRepository()
    rows = await repository.list_deadlines(
        project_ids=ids,
        assignee_id=assignee_id,
        start=start.isoformat() if start else None,
        end=end.isoformat() if end else None,
        include_done=include_done,
    )
    if not rows:
        return []

    assignee_ids = sorted({str(row.get("assignee_id") or "") for row in rows} - {""})
    members = await repository.get_members_by_ids(assignee_ids) if assignee_ids else []
    names = {str(row["id"]): str(row.get("display_name") or "Member") for row in members}

    deadlines: list[dict[str, Any]] = []
    for row in rows:
        due = _iso_date(row.get("due_date"))
        if due is None:
            continue
        assignee = str(row.get("assignee_id") or "")
        deadlines.append(
            {
                "ticket_id": str(row["id"]),
                "project_id": str(row["project_id"]),
                "number": int(row.get("number") or 0),
                "title": str(row.get("title") or ""),
                "status": str(row.get("status") or "todo"),
                "priority": str(row.get("priority") or "medium"),
                "due_date": due,
                "assignee": (
                    {"id": assignee, "display_name": names.get(assignee, "Member")}
                    if assignee
                    else None
                ),
            }
        )
    deadlines.sort(key=lambda item: (item["due_date"], item["number"]))
    return deadlines
