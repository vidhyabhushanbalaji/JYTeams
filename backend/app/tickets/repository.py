"""Persistence for the Tickets section.

The protocol keeps the service testable (the tests use an in-memory repository); the Supabase
implementation is a thin PostgREST wrapper and does no business logic. Membership *checks* are
not here — they belong to :class:`app.core.access.ProjectAccess`, which every section shares.
"""

from __future__ import annotations

from typing import Any, Protocol

from fastapi import HTTPException, status
from postgrest.exceptions import APIError
from starlette.concurrency import run_in_threadpool

from app.db.supabase import admin_client

Row = dict[str, Any]


class TicketRequestError(HTTPException):
    """Supabase/PostgREST rejected a request (API key, schema or constraint problem)."""

    def __init__(self, message: str) -> None:
        super().__init__(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=message)


def _describe_api_error(exc: APIError) -> str:
    """Turn a PostgREST error into something that says what to fix."""
    message = str(getattr(exc, "message", None) or exc)
    code = getattr(exc, "code", None)
    if code == "42501":
        message += (
            " - the request ran without service-role privileges; check that"
            " SUPABASE_SERVICE_ROLE_KEY holds the secret key (sb_secret_...) and not the"
            " publishable key, then restart the API"
        )
    elif code == "23503":
        message += (
            " - a referenced row is missing; the identity must be a member id from"
            " POST /api/tickets/members (migration 0003 creates the table)"
        )
    elif code == "23505":
        message += " - that name or ticket number already exists"
    if getattr(exc, "hint", None):
        message += f" (hint: {exc.hint})"
    return f"Supabase rejected the request: {message}"


class TicketRepository(Protocol):
    """Data access used by :class:`app.tickets.service.TicketService`."""

    # -- members ---------------------------------------------------------------
    async def find_member(self, name_key: str) -> Row | None: ...

    async def get_member(self, member_id: str) -> Row | None: ...

    async def list_members(self) -> list[Row]: ...

    async def create_member(self, display_name: str) -> Row: ...

    async def get_members_by_ids(self, member_ids: list[str]) -> list[Row]: ...

    # -- projects --------------------------------------------------------------
    async def get_project(self, project_id: str) -> Row | None: ...

    async def list_projects_by_ids(self, project_ids: list[str]) -> list[Row]: ...

    async def list_project_members(self, project_id: str) -> list[Row]: ...

    async def add_project_member(
        self, *, project_id: str, member_id: str, role: str, added_by: str | None
    ) -> Row: ...

    async def remove_project_member(self, project_id: str, member_id: str) -> bool: ...

    # -- tickets ---------------------------------------------------------------
    async def next_ticket_number(self, project_id: str) -> int: ...

    async def create_ticket(self, payload: Row) -> Row: ...

    async def get_ticket(self, ticket_id: str) -> Row | None: ...

    async def list_tickets(
        self,
        *,
        project_ids: list[str],
        assignee_id: str | None = None,
        status: str | None = None,
        limit: int = 500,
    ) -> list[Row]: ...

    async def update_ticket(self, ticket_id: str, fields: Row) -> Row: ...

    async def list_ticket_counts(self, ticket_ids: list[str]) -> dict[str, tuple[int, int]]:
        """``ticket_id -> (attachments, comments)`` for the list view."""
        ...

    async def get_tickets_by_ids(self, ticket_ids: list[str]) -> list[Row]:
        """Ticket number/title lookups for the activity feed."""
        ...

    async def list_deadlines(
        self,
        *,
        project_ids: list[str],
        assignee_id: str | None = None,
        start: str | None = None,
        end: str | None = None,
        include_done: bool = False,
    ) -> list[Row]:
        """Tickets with a due date, for the calendar (read-only; never a model call)."""
        ...

    # -- project content -------------------------------------------------------
    async def list_files(self, project_id: str) -> list[Row]: ...

    async def list_directories(self, project_id: str) -> list[Row]: ...

    async def get_file(self, file_id: str) -> Row | None: ...

    # -- attachments -----------------------------------------------------------
    async def list_attachments(self, ticket_id: str) -> list[Row]: ...

    async def add_attachment(
        self, *, ticket_id: str, file_id: str, added_by: str, source: str
    ) -> Row: ...

    async def remove_attachment(self, ticket_id: str, file_id: str) -> bool: ...

    # -- comments --------------------------------------------------------------
    async def list_comments(self, ticket_id: str) -> list[Row]: ...

    async def create_comment(self, *, ticket_id: str, author_id: str, body: str) -> Row: ...

    # -- activity --------------------------------------------------------------
    async def list_events(
        self, *, project_ids: list[str], ticket_id: str | None = None, limit: int = 100
    ) -> list[Row]: ...


class SupabaseTicketRepository:
    """PostgREST-backed repository (service role client, so RLS does not apply)."""

    async def _run(self, operation):
        """Run a blocking PostgREST call, surfacing Supabase errors as HTTP errors."""
        try:
            return await run_in_threadpool(operation)
        except APIError as exc:
            raise TicketRequestError(_describe_api_error(exc)) from exc

    async def _one(self, builder_factory) -> Row | None:
        response = await self._run(lambda: builder_factory().limit(1).execute())
        rows = response.data or []
        return dict(rows[0]) if rows else None

    # -- members ---------------------------------------------------------------

    async def find_member(self, name_key: str) -> Row | None:
        return await self._one(
            lambda: admin_client().table("members").select("*").eq("name_key", name_key)
        )

    async def get_member(self, member_id: str) -> Row | None:
        return await self._one(
            lambda: admin_client().table("members").select("*").eq("id", member_id)
        )

    async def list_members(self) -> list[Row]:
        def run() -> list[Row]:
            response = admin_client().table("members").select("*").order("display_name").execute()
            return response.data or []

        return await self._run(run)

    async def create_member(self, display_name: str) -> Row:
        """Insert a member. Losing a race on the unique name returns the existing row."""

        def run() -> Row:
            try:
                response = (
                    admin_client().table("members").insert({"display_name": display_name}).execute()
                )
                return response.data[0]
            except APIError as exc:
                if getattr(exc, "code", None) != "23505":
                    raise
                existing = (
                    admin_client()
                    .table("members")
                    .select("*")
                    .eq("name_key", display_name.strip().lower())
                    .limit(1)
                    .execute()
                )
                rows = existing.data or []
                if not rows:
                    raise
                return rows[0]

        return await self._run(run)

    async def get_members_by_ids(self, member_ids: list[str]) -> list[Row]:
        if not member_ids:
            return []

        def run() -> list[Row]:
            response = admin_client().table("members").select("*").in_("id", member_ids).execute()
            return response.data or []

        return await self._run(run)

    # -- projects --------------------------------------------------------------

    async def get_project(self, project_id: str) -> Row | None:
        return await self._one(
            lambda: admin_client().table("projects").select("*").eq("id", project_id)
        )

    async def list_projects_by_ids(self, project_ids: list[str]) -> list[Row]:
        if not project_ids:
            return []

        def run() -> list[Row]:
            response = (
                admin_client()
                .table("projects")
                .select("id, name, owner_id")
                .in_("id", project_ids)
                .execute()
            )
            return response.data or []

        return await self._run(run)

    async def list_project_members(self, project_id: str) -> list[Row]:
        def run() -> list[Row]:
            response = (
                admin_client()
                .table("project_members")
                .select("member_id, role, added_at")
                .eq("project_id", project_id)
                .execute()
            )
            rows = response.data or []
            ids = [str(row["member_id"]) for row in rows]
            if not ids:
                return rows
            members = (
                admin_client().table("members").select("id, display_name").in_("id", ids).execute()
            )
            names = {str(item["id"]): str(item["display_name"]) for item in (members.data or [])}
            return [
                {**row, "display_name": names.get(str(row["member_id"]), "Member")} for row in rows
            ]

        return await self._run(run)

    async def add_project_member(
        self, *, project_id: str, member_id: str, role: str, added_by: str | None
    ) -> Row:
        def run() -> Row:
            response = (
                admin_client()
                .table("project_members")
                .upsert(
                    {
                        "project_id": project_id,
                        "member_id": member_id,
                        "role": role,
                        "added_by": added_by,
                    },
                    on_conflict="project_id,member_id",
                )
                .execute()
            )
            return response.data[0]

        return await self._run(run)

    async def remove_project_member(self, project_id: str, member_id: str) -> bool:
        def run() -> bool:
            response = (
                admin_client()
                .table("project_members")
                .delete()
                .eq("project_id", project_id)
                .eq("member_id", member_id)
                .execute()
            )
            return bool(response.data)

        return await self._run(run)

    # -- tickets ---------------------------------------------------------------

    async def next_ticket_number(self, project_id: str) -> int:
        def run() -> int:
            response = (
                admin_client()
                .table("tickets")
                .select("number")
                .eq("project_id", project_id)
                .order("number", desc=True)
                .limit(1)
                .execute()
            )
            rows = response.data or []
            return int(rows[0]["number"]) + 1 if rows else 1

        return await self._run(run)

    async def create_ticket(self, payload: Row) -> Row:
        def run() -> Row:
            response = admin_client().table("tickets").insert(payload).execute()
            return response.data[0]

        return await self._run(run)

    async def get_ticket(self, ticket_id: str) -> Row | None:
        return await self._one(
            lambda: admin_client().table("tickets").select("*").eq("id", ticket_id)
        )

    async def list_tickets(
        self,
        *,
        project_ids: list[str],
        assignee_id: str | None = None,
        status: str | None = None,
        limit: int = 500,
    ) -> list[Row]:
        if not project_ids:
            return []

        def run() -> list[Row]:
            builder = admin_client().table("tickets").select("*").in_("project_id", project_ids)
            if assignee_id:
                builder = builder.eq("assignee_id", assignee_id)
            if status:
                builder = builder.eq("status", status)
            response = builder.order("created_at", desc=True).limit(limit).execute()
            return response.data or []

        return await self._run(run)

    async def update_ticket(self, ticket_id: str, fields: Row) -> Row:
        def run() -> Row:
            response = admin_client().table("tickets").update(fields).eq("id", ticket_id).execute()
            return response.data[0]

        return await self._run(run)

    async def list_ticket_counts(self, ticket_ids: list[str]) -> dict[str, tuple[int, int]]:
        """`ticket_id -> (attachments, comments)`, in two queries for the whole list."""
        if not ticket_ids:
            return {}

        def run() -> dict[str, tuple[int, int]]:
            counts: dict[str, list[int]] = {ticket_id: [0, 0] for ticket_id in ticket_ids}
            files = (
                admin_client()
                .table("ticket_files")
                .select("ticket_id")
                .in_("ticket_id", ticket_ids)
                .execute()
            )
            for row in files.data or []:
                counts.setdefault(str(row["ticket_id"]), [0, 0])[0] += 1
            comments = (
                admin_client()
                .table("ticket_comments")
                .select("ticket_id")
                .in_("ticket_id", ticket_ids)
                .execute()
            )
            for row in comments.data or []:
                counts.setdefault(str(row["ticket_id"]), [0, 0])[1] += 1
            return {ticket_id: (values[0], values[1]) for ticket_id, values in counts.items()}

        return await self._run(run)

    async def get_tickets_by_ids(self, ticket_ids: list[str]) -> list[Row]:
        if not ticket_ids:
            return []

        def run() -> list[Row]:
            response = (
                admin_client()
                .table("tickets")
                .select("id, number, title, project_id")
                .in_("id", ticket_ids)
                .execute()
            )
            return response.data or []

        return await self._run(run)

    async def list_deadlines(
        self,
        *,
        project_ids: list[str],
        assignee_id: str | None = None,
        start: str | None = None,
        end: str | None = None,
        include_done: bool = False,
    ) -> list[Row]:
        """Tickets carrying a due date, ordered by that date.

        ``start`` and ``end`` are inclusive ISO dates; ``include_done`` is False by default so a
        finished ticket stops shadowing the calendar.
        """
        if not project_ids:
            return []

        def run() -> list[Row]:
            builder = (
                admin_client()
                .table("tickets")
                .select("id, project_id, number, title, status, priority, due_date, assignee_id")
                .in_("project_id", project_ids)
                .not_.is_("due_date", "null")
            )
            if assignee_id:
                builder = builder.eq("assignee_id", assignee_id)
            if not include_done:
                builder = builder.neq("status", "done")
            if start:
                builder = builder.gte("due_date", start)
            if end:
                builder = builder.lte("due_date", end)
            response = builder.order("due_date").execute()
            return response.data or []

        return await self._run(run)

    # -- project content -------------------------------------------------------

    async def list_files(self, project_id: str) -> list[Row]:
        def run() -> list[Row]:
            response = (
                admin_client()
                .table("files")
                .select("id, name, path, directory_id, size_bytes, updated_at")
                .eq("project_id", project_id)
                .execute()
            )
            return response.data or []

        return await self._run(run)

    async def list_directories(self, project_id: str) -> list[Row]:
        def run() -> list[Row]:
            response = (
                admin_client()
                .table("directories")
                .select("id, path, name")
                .eq("project_id", project_id)
                .execute()
            )
            return response.data or []

        return await self._run(run)

    async def get_file(self, file_id: str) -> Row | None:
        return await self._one(lambda: admin_client().table("files").select("*").eq("id", file_id))

    # -- attachments -----------------------------------------------------------

    async def list_attachments(self, ticket_id: str) -> list[Row]:
        def run() -> list[Row]:
            response = (
                admin_client()
                .table("ticket_files")
                .select("file_id, added_by, source, added_at")
                .eq("ticket_id", ticket_id)
                .order("added_at")
                .execute()
            )
            return response.data or []

        return await self._run(run)

    async def add_attachment(
        self, *, ticket_id: str, file_id: str, added_by: str, source: str
    ) -> Row:
        def run() -> Row:
            response = (
                admin_client()
                .table("ticket_files")
                .upsert(
                    {
                        "ticket_id": ticket_id,
                        "file_id": file_id,
                        "added_by": added_by,
                        "source": source,
                    },
                    on_conflict="ticket_id,file_id",
                )
                .execute()
            )
            return response.data[0]

        return await self._run(run)

    async def remove_attachment(self, ticket_id: str, file_id: str) -> bool:
        def run() -> bool:
            response = (
                admin_client()
                .table("ticket_files")
                .delete()
                .eq("ticket_id", ticket_id)
                .eq("file_id", file_id)
                .execute()
            )
            return bool(response.data)

        return await self._run(run)

    # -- comments --------------------------------------------------------------

    async def list_comments(self, ticket_id: str) -> list[Row]:
        def run() -> list[Row]:
            response = (
                admin_client()
                .table("ticket_comments")
                .select("*")
                .eq("ticket_id", ticket_id)
                .order("created_at")
                .execute()
            )
            return response.data or []

        return await self._run(run)

    async def create_comment(self, *, ticket_id: str, author_id: str, body: str) -> Row:
        def run() -> Row:
            response = (
                admin_client()
                .table("ticket_comments")
                .insert({"ticket_id": ticket_id, "author_id": author_id, "body": body})
                .execute()
            )
            return response.data[0]

        return await self._run(run)

    # -- activity --------------------------------------------------------------

    async def list_events(
        self, *, project_ids: list[str], ticket_id: str | None = None, limit: int = 100
    ) -> list[Row]:
        if not project_ids:
            return []

        def run() -> list[Row]:
            builder = (
                admin_client().table("ticket_events").select("*").in_("project_id", project_ids)
            )
            if ticket_id:
                builder = builder.eq("ticket_id", ticket_id)
            response = builder.order("created_at", desc=True).limit(limit).execute()
            return response.data or []

        return await self._run(run)
