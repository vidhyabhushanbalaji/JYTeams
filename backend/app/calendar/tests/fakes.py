"""In-memory collaborators so the calendar is tested without Supabase or a network."""

from __future__ import annotations

import itertools
from collections.abc import Sequence
from datetime import UTC, date, datetime, time
from typing import Any

from app.core.access import ProjectAccess, ProjectRole

Row = dict[str, Any]


def _moment(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


class FakeProjectAccess(ProjectAccess):
    """Membership read from the fake repository's ``memberships`` map."""

    def __init__(self, repository: InMemoryCalendarRepository) -> None:
        self._repository = repository

    async def role(self, project_id: str, member_id: str) -> ProjectRole | None:
        value = self._repository.memberships.get((project_id, member_id))
        return ProjectRole(value) if value else None

    async def project_ids(self, member_id: str) -> list[str]:
        return sorted(
            project_id
            for (project_id, member), _ in self._repository.memberships.items()
            if member == member_id
        )


class InMemoryCalendarRepository:
    """A PostgREST stand-in for ``calendar_events`` (plus the reads it needs)."""

    def __init__(self) -> None:
        self.members: dict[str, Row] = {}
        self.projects: dict[str, Row] = {}
        self.memberships: dict[tuple[str, str], str] = {}
        self.events: dict[str, Row] = {}
        self._ids = itertools.count(1)

    # -- seeding ---------------------------------------------------------------

    def seed_member(self, display_name: str, member_id: str | None = None) -> Row:
        row = {
            "id": member_id or f"member-{next(self._ids)}",
            "display_name": display_name,
            "name_key": display_name.strip().lower(),
        }
        self.members[row["id"]] = row
        return dict(row)

    def seed_project(self, name: str, owner_id: str, project_id: str | None = None) -> Row:
        row = {
            "id": project_id or f"project-{next(self._ids)}",
            "name": name,
            "owner_id": owner_id,
        }
        self.projects[row["id"]] = row
        self.memberships[(row["id"], owner_id)] = "owner"
        return dict(row)

    def share(self, project_id: str, member_id: str, role: str = "member") -> None:
        self.memberships[(project_id, member_id)] = role

    def seed_event(
        self,
        *,
        member_id: str,
        title: str,
        starts_at: str,
        project_id: str | None = None,
        ends_at: str | None = None,
        all_day: bool = False,
        notes: str = "",
    ) -> Row:
        row = {
            "id": f"event-{next(self._ids)}",
            "project_id": project_id,
            "member_id": member_id,
            "title": title,
            "notes": notes,
            "starts_at": starts_at,
            "ends_at": ends_at,
            "all_day": all_day,
            "created_at": starts_at,
            "updated_at": starts_at,
        }
        self.events[row["id"]] = row
        return dict(row)

    # -- events ----------------------------------------------------------------

    async def list_personal_events(
        self, *, member_id: str, start: datetime, end: datetime
    ) -> list[Row]:
        return [
            dict(row)
            for row in self.events.values()
            if row["project_id"] is None
            and row["member_id"] == member_id
            and start <= _moment(row["starts_at"]) <= end
        ]

    async def list_project_events(
        self, *, project_ids: list[str], start: datetime, end: datetime
    ) -> list[Row]:
        return [
            dict(row)
            for row in self.events.values()
            if row["project_id"] in project_ids and start <= _moment(row["starts_at"]) <= end
        ]

    async def get_event(self, event_id: str) -> Row | None:
        row = self.events.get(event_id)
        return dict(row) if row else None

    async def insert_event(self, payload: Row) -> Row:
        row = {
            **payload,
            "id": f"event-{next(self._ids)}",
            "created_at": payload["starts_at"],
            "updated_at": payload["starts_at"],
        }
        self.events[row["id"]] = row
        return dict(row)

    async def update_event(self, event_id: str, fields: Row) -> Row:
        self.events[event_id].update(fields)
        return dict(self.events[event_id])

    async def delete_event(self, event_id: str) -> bool:
        return self.events.pop(event_id, None) is not None

    # -- shared reads ----------------------------------------------------------

    async def list_projects_by_ids(self, project_ids: list[str]) -> list[Row]:
        return [dict(self.projects[pid]) for pid in project_ids if pid in self.projects]

    async def list_members_by_ids(self, member_ids: list[str]) -> list[Row]:
        return [dict(self.members[mid]) for mid in member_ids if mid in self.members]


class FakeDeadlines:
    """Stands in for ``app.tickets.public.list_deadlines`` and records what it was asked."""

    def __init__(self, repository: InMemoryCalendarRepository) -> None:
        self._repository = repository
        self.rows: list[Row] = []
        self.calls: list[dict[str, Any]] = []

    def seed(
        self,
        *,
        project_id: str,
        ticket_id: str,
        title: str,
        due_date: date,
        assignee_id: str | None = None,
        number: int = 1,
        status: str = "todo",
        priority: str = "medium",
    ) -> Row:
        row = {
            "ticket_id": ticket_id,
            "project_id": project_id,
            "number": number,
            "title": title,
            "status": status,
            "priority": priority,
            "due_date": due_date.isoformat(),
            "assignee": None,
        }
        if assignee_id:
            member = self._repository.members.get(assignee_id) or {}
            row["assignee"] = {
                "id": assignee_id,
                "display_name": str(member.get("display_name") or "Member"),
            }
        self.rows.append(row)
        return dict(row)

    async def list_deadlines(
        self,
        *,
        project_ids: Sequence[str],
        assignee_id: str | None,
        start: date,
        end: date,
    ) -> list[dict[str, Any]]:
        self.calls.append(
            {
                "project_ids": list(project_ids),
                "assignee_id": assignee_id,
                "start": start,
                "end": end,
            }
        )
        found: list[dict[str, Any]] = []
        for row in self.rows:
            if row["project_id"] not in project_ids:
                continue
            if assignee_id and (row.get("assignee") or {}).get("id") != assignee_id:
                continue
            due = date.fromisoformat(row["due_date"])
            if not start <= due <= end:
                continue
            found.append(dict(row))
        return found


def at(day: date, hour: int = 9) -> str:
    """An ISO timestamp on ``day`` (used by the seeded events)."""
    return datetime.combine(day, time(hour=hour), tzinfo=UTC).isoformat()
