"""In-memory collaborators so the tickets section is tested without Supabase or a network."""

from __future__ import annotations

import itertools
from collections.abc import Mapping
from typing import Any

from app.core.access import ProjectAccess, ProjectRole
from app.core.activity import ActivityLog
from app.tickets.distill import LocalDistiller, SearchTerms

Row = dict[str, Any]


class InMemoryTicketRepository:
    """A PostgREST stand-in: rows live in dicts and ids are sequential."""

    def __init__(self) -> None:
        self.members: dict[str, Row] = {}
        self.projects: dict[str, Row] = {}
        self.memberships: dict[tuple[str, str], Row] = {}
        self.tickets: dict[str, Row] = {}
        self.files: dict[str, Row] = {}
        self.directories: dict[str, Row] = {}
        self.attachments: list[Row] = []
        self.comments: dict[str, Row] = {}
        self.events: list[Row] = []
        self._ids = itertools.count(1)

    def _next(self, prefix: str) -> str:
        return f"{prefix}-{next(self._ids)}"

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
        self.memberships[(row["id"], owner_id)] = {
            "member_id": owner_id,
            "role": "owner",
            "added_by": None,
            "added_at": "2026-01-01T00:00:00+00:00",
        }
        return dict(row)

    def seed_directory(self, project_id: str, name: str, path: str) -> Row:
        row = {"id": self._next("directory"), "project_id": project_id, "name": name, "path": path}
        self.directories[row["id"]] = row
        return dict(row)

    def seed_file(
        self,
        project_id: str,
        *,
        directory_id: str,
        name: str,
        path: str = "",
        size_bytes: int = 10,
        updated_at: str = "2026-01-01T00:00:00+00:00",
    ) -> Row:
        row = {
            "id": self._next("file"),
            "project_id": project_id,
            "directory_id": directory_id,
            "name": name,
            "path": path or name,
            "size_bytes": size_bytes,
            "updated_at": updated_at,
        }
        self.files[row["id"]] = row
        return dict(row)

    # -- members ---------------------------------------------------------------

    async def find_member(self, name_key: str) -> Row | None:
        return next(
            (dict(row) for row in self.members.values() if row["name_key"] == name_key), None
        )

    async def get_member(self, member_id: str) -> Row | None:
        row = self.members.get(member_id)
        return dict(row) if row else None

    async def list_members(self) -> list[Row]:
        return sorted(
            (dict(row) for row in self.members.values()), key=lambda row: row["display_name"]
        )

    async def create_member(self, display_name: str) -> Row:
        return self.seed_member(display_name)

    async def get_members_by_ids(self, member_ids: list[str]) -> list[Row]:
        return [
            dict(self.members[member_id]) for member_id in member_ids if member_id in self.members
        ]

    # -- projects --------------------------------------------------------------

    async def get_project(self, project_id: str) -> Row | None:
        row = self.projects.get(project_id)
        return dict(row) if row else None

    async def list_projects_by_ids(self, project_ids: list[str]) -> list[Row]:
        return [dict(self.projects[pid]) for pid in project_ids if pid in self.projects]

    async def list_project_members(self, project_id: str) -> list[Row]:
        rows = []
        for (pid, member_id), membership in self.memberships.items():
            if pid != project_id:
                continue
            member = self.members.get(member_id, {})
            rows.append(
                {
                    "member_id": member_id,
                    "display_name": member.get("display_name", "Member"),
                    "role": membership["role"],
                    "added_at": membership.get("added_at"),
                }
            )
        return rows

    async def add_project_member(
        self, *, project_id: str, member_id: str, role: str, added_by: str | None
    ) -> Row:
        row = {
            "member_id": member_id,
            "role": role,
            "added_by": added_by,
            "added_at": "2026-01-02T00:00:00+00:00",
        }
        self.memberships[(project_id, member_id)] = row
        return dict(row)

    async def remove_project_member(self, project_id: str, member_id: str) -> bool:
        return self.memberships.pop((project_id, member_id), None) is not None

    # -- tickets ---------------------------------------------------------------

    async def next_ticket_number(self, project_id: str) -> int:
        numbers = [
            int(row["number"]) for row in self.tickets.values() if row["project_id"] == project_id
        ]
        return max(numbers, default=0) + 1

    async def create_ticket(self, payload: Row) -> Row:
        row = {"id": self._next("ticket"), **payload}
        row.setdefault("created_at", "2026-01-03T00:00:00+00:00")
        row.setdefault("updated_at", row["created_at"])
        self.tickets[row["id"]] = row
        return dict(row)

    async def get_ticket(self, ticket_id: str) -> Row | None:
        row = self.tickets.get(ticket_id)
        return dict(row) if row else None

    async def list_tickets(
        self,
        *,
        project_ids: list[str],
        assignee_id: str | None = None,
        status: str | None = None,
        limit: int = 500,
    ) -> list[Row]:
        rows = [
            dict(row)
            for row in self.tickets.values()
            if row["project_id"] in project_ids
            and (assignee_id is None or row.get("assignee_id") == assignee_id)
            and (status is None or row.get("status") == status)
        ]
        return rows[:limit]

    async def update_ticket(self, ticket_id: str, fields: Row) -> Row:
        self.tickets[ticket_id].update(fields)
        return dict(self.tickets[ticket_id])

    async def list_ticket_counts(self, ticket_ids: list[str]) -> dict[str, tuple[int, int]]:
        return {
            ticket_id: (
                len([row for row in self.attachments if row["ticket_id"] == ticket_id]),
                len([row for row in self.comments.values() if row["ticket_id"] == ticket_id]),
            )
            for ticket_id in ticket_ids
        }

    async def get_tickets_by_ids(self, ticket_ids: list[str]) -> list[Row]:
        return [dict(self.tickets[tid]) for tid in ticket_ids if tid in self.tickets]

    # -- project content -------------------------------------------------------

    async def list_files(self, project_id: str) -> list[Row]:
        return [dict(row) for row in self.files.values() if row["project_id"] == project_id]

    async def list_directories(self, project_id: str) -> list[Row]:
        return [dict(row) for row in self.directories.values() if row["project_id"] == project_id]

    async def get_file(self, file_id: str) -> Row | None:
        row = self.files.get(file_id)
        return dict(row) if row else None

    # -- attachments -----------------------------------------------------------

    async def list_attachments(self, ticket_id: str) -> list[Row]:
        return [dict(row) for row in self.attachments if row["ticket_id"] == ticket_id]

    async def add_attachment(
        self, *, ticket_id: str, file_id: str, added_by: str, source: str
    ) -> Row:
        for row in self.attachments:
            if row["ticket_id"] == ticket_id and row["file_id"] == file_id:
                return dict(row)
        row = {
            "ticket_id": ticket_id,
            "file_id": file_id,
            "added_by": added_by,
            "source": source,
            "added_at": "2026-01-04T00:00:00+00:00",
        }
        self.attachments.append(row)
        return dict(row)

    async def remove_attachment(self, ticket_id: str, file_id: str) -> bool:
        for index, row in enumerate(self.attachments):
            if row["ticket_id"] == ticket_id and row["file_id"] == file_id:
                self.attachments.pop(index)
                return True
        return False

    # -- comments --------------------------------------------------------------

    async def list_comments(self, ticket_id: str) -> list[Row]:
        return [dict(row) for row in self.comments.values() if row["ticket_id"] == ticket_id]

    async def create_comment(self, *, ticket_id: str, author_id: str, body: str) -> Row:
        row = {
            "id": self._next("comment"),
            "ticket_id": ticket_id,
            "author_id": author_id,
            "body": body,
            "created_at": "2026-01-05T00:00:00+00:00",
        }
        self.comments[row["id"]] = row
        return dict(row)

    # -- activity --------------------------------------------------------------

    async def list_events(
        self, *, project_ids: list[str], ticket_id: str | None = None, limit: int = 100
    ) -> list[Row]:
        rows = [
            dict(row)
            for row in self.events
            if row["project_id"] in project_ids
            and (ticket_id is None or row.get("ticket_id") == ticket_id)
        ]
        return list(reversed(rows))[:limit]


class FakeProjectAccess(ProjectAccess):
    """Membership answered from the in-memory repository (sharing shows up immediately)."""

    def __init__(self, repository: InMemoryTicketRepository) -> None:
        self._repository = repository

    async def role(self, project_id: str, member_id: str) -> ProjectRole | None:
        row = self._repository.memberships.get((project_id, member_id))
        return ProjectRole(row["role"]) if row else None

    async def project_ids(self, member_id: str) -> list[str]:
        return [
            project_id
            for (project_id, member) in self._repository.memberships
            if member == member_id
        ]


class FakeDistiller:
    """Scripted distillation: records the wording it saw and returns fixed search terms.

    Without a scripted result it behaves like the offline distiller the app uses when no key is
    configured, so tests that do not care about the model still exercise a real reduction.
    """

    model_name = "fake"

    def __init__(self, result: SearchTerms | None = None) -> None:
        self.result = result
        #: When set, every call raises it — how a model outage is simulated.
        self.error: Exception | None = None
        self.calls: list[Row] = []

    async def terms(self, *, title: str, description: str) -> SearchTerms:
        self.calls.append({"title": title, "description": description})
        if self.error is not None:
            raise self.error
        if self.result is not None:
            return self.result
        return await LocalDistiller().terms(title=title, description=description)


class FakeTicketSearch:
    """Scripted Graph AI Search: records the queries and returns fixed hits."""

    def __init__(self, hits: list[Row] | None = None) -> None:
        self.hits = list(hits or [])
        self.calls: list[Row] = []

    async def search(
        self,
        *,
        project_id: str,
        member_id: str,
        query: str,
        context: str,
        limit: int,
    ) -> dict[str, Any]:
        self.calls.append(
            {
                "project_id": project_id,
                "member_id": member_id,
                "query": query,
                "context": context,
                "limit": limit,
            }
        )
        return {"results": [dict(hit) for hit in self.hits[:limit]]}


class RecordingActivity(ActivityLog):
    """Collects the events the service wrote, and mirrors them into the repository.

    Production writes ``ticket_events`` (``SupabaseActivityLog``); mirroring here means the
    service's feed reads see exactly what the log recorded.
    """

    def __init__(self, repository: InMemoryTicketRepository | None = None) -> None:
        self.events: list[Row] = []
        self._repository = repository

    async def record(
        self,
        *,
        project_id: str,
        member_id: str | None,
        kind: str,
        detail: Mapping[str, Any] | None = None,
        ticket_id: str | None = None,
    ) -> None:
        event = {
            "id": f"event-{len(self.events) + 1}",
            "project_id": project_id,
            "member_id": member_id,
            "kind": kind,
            "detail": dict(detail or {}),
            "ticket_id": ticket_id,
            "created_at": f"2026-01-06T00:00:{len(self.events):02d}+00:00",
        }
        self.events.append(event)
        if self._repository is not None:
            self._repository.events.append(dict(event))

    def kinds(self) -> list[str]:
        return [str(event["kind"]) for event in self.events]
