"""In-memory collaborators so the chat section is tested without Supabase or a network."""

from __future__ import annotations

import itertools
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import Any

from app.chat.mentions import Mention
from app.core.access import ProjectAccess, ProjectRole

Row = dict[str, Any]


class FakeProjectAccess(ProjectAccess):
    """Membership read from the fake repository's ``memberships`` map."""

    def __init__(self, repository: InMemoryChatRepository) -> None:
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


class InMemoryChatRepository:
    """A PostgREST stand-in: rows live in dicts and ids are sequential."""

    def __init__(self) -> None:
        self.members: dict[str, Row] = {}
        self.projects: dict[str, Row] = {}
        self.memberships: dict[tuple[str, str], str] = {}
        self.messages: list[Row] = []
        self._ids = itertools.count(1)
        self._seq = itertools.count(1)
        self._clock = datetime(2026, 1, 1, 9, 0, tzinfo=UTC)

    def _next(self, prefix: str) -> str:
        return f"{prefix}-{next(self._ids)}"

    def _now(self) -> str:
        self._clock = self._clock + timedelta(minutes=1)
        return self._clock.isoformat()

    # -- seeding ---------------------------------------------------------------

    def seed_member(self, display_name: str, member_id: str | None = None) -> Row:
        row = {
            "id": member_id or self._next("member"),
            "display_name": display_name,
            "name_key": display_name.strip().lower(),
        }
        self.members[row["id"]] = row
        return dict(row)

    def seed_project(self, name: str, owner_id: str, project_id: str | None = None) -> Row:
        row = {"id": project_id or self._next("project"), "name": name, "owner_id": owner_id}
        self.projects[row["id"]] = row
        self.memberships[(row["id"], owner_id)] = "owner"
        return dict(row)

    def share(self, project_id: str, member_id: str, role: str = "member") -> None:
        self.memberships[(project_id, member_id)] = role

    # -- messages --------------------------------------------------------------

    async def insert_message(self, payload: Row) -> Row:
        row = {
            **payload,
            "seq": next(self._seq),
            "id": self._next("message"),
            "created_at": self._now(),
        }
        self.messages.append(row)
        return dict(row)

    async def get_message(self, message_id: str) -> Row | None:
        row = next((item for item in self.messages if item["id"] == message_id), None)
        return dict(row) if row else None

    async def list_messages(
        self, *, project_id: str, after_seq: int | None = None, limit: int = 50
    ) -> list[Row]:
        rows = [row for row in self.messages if row["project_id"] == project_id]
        rows.sort(key=lambda row: row["seq"])
        if after_seq is not None:
            return [dict(row) for row in rows if row["seq"] > after_seq][:limit]
        return [dict(row) for row in rows[-limit:]]

    async def latest_message(self, project_id: str) -> Row | None:
        rows = [row for row in self.messages if row["project_id"] == project_id]
        if not rows:
            return None
        return dict(max(rows, key=lambda row: row["seq"]))

    async def update_message(self, message_id: str, fields: Row) -> Row:
        row = next(item for item in self.messages if item["id"] == message_id)
        row.update(fields)
        return dict(row)

    # -- shared reads ----------------------------------------------------------

    async def list_projects_by_ids(self, project_ids: list[str]) -> list[Row]:
        return [dict(self.projects[pid]) for pid in project_ids if pid in self.projects]

    async def list_members_by_ids(self, member_ids: list[str]) -> list[Row]:
        return [dict(self.members[mid]) for mid in member_ids if mid in self.members]


class FakeMentionCatalogue:
    """Documents, folders and tickets that belong to one project each."""

    def __init__(self) -> None:
        self.targets: dict[tuple[str, str], dict[str, Any]] = {}
        self.searches: list[tuple[str, str]] = []

    def seed_target(
        self,
        project_id: str,
        *,
        kind: str,
        target_id: str | None = None,
        label: str,
        path: str = "",
        directory_path: str = "",
        ticket_number: int | None = None,
        event_day: str | None = None,
    ) -> dict[str, Any]:
        target = {
            "kind": kind,
            "id": target_id or f"{kind}-{len(self.targets) + 1}",
            "label": label,
            "path": path,
            "directory_path": directory_path,
            "ticket_number": ticket_number,
            "event_day": event_day,
            "detail": kind,
            "project_id": project_id,
        }
        self.targets[(kind, target["id"])] = target
        return target

    async def search(self, *, project_id: str, query: str, limit: int) -> list[dict[str, Any]]:
        self.searches.append((project_id, query))
        needle = (query or "").casefold()
        rows = [
            {key: value for key, value in target.items() if key != "project_id"}
            for target in self.targets.values()
            if target["project_id"] == project_id
            and (not needle or needle in str(target["label"]).casefold())
        ]
        return rows[:limit]

    async def describe(
        self, *, project_id: str, mentions: Sequence[Mention]
    ) -> dict[tuple[str, str], dict[str, Any]]:
        found: dict[tuple[str, str], dict[str, Any]] = {}
        for mention in mentions:
            target = self.targets.get(mention.key)
            if target is None or target["project_id"] != project_id:
                continue
            found[mention.key] = {
                key: value for key, value in target.items() if key != "project_id"
            }
        return found
