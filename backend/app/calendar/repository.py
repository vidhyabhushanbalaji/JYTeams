"""Persistence for the Calendar section.

The protocol keeps the service testable (the tests use an in-memory repository); the Supabase
implementation is a thin PostgREST wrapper. Membership and event ownership are decided in the
service (:mod:`app.core.access` and the creator check), never here.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol

from fastapi import HTTPException, status
from postgrest.exceptions import APIError
from starlette.concurrency import run_in_threadpool

from app.db.supabase import admin_client

Row = dict[str, Any]


class CalendarRequestError(HTTPException):
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
            " - a referenced row is missing; apply supabase/migrations/0006_calendar.sql and make"
            " sure the member id comes from POST /api/tickets/members"
        )
    elif code == "23514":
        message += " - an event cannot end before it starts"
    if getattr(exc, "hint", None):
        message += f" (hint: {exc.hint})"
    return f"Supabase rejected the request: {message}"


class CalendarRepository(Protocol):
    """Data access used by :class:`app.calendar.service.CalendarService`."""

    async def list_personal_events(
        self, *, member_id: str, start: datetime, end: datetime
    ) -> list[Row]: ...

    async def list_project_events(
        self, *, project_ids: list[str], start: datetime, end: datetime
    ) -> list[Row]: ...

    async def get_event(self, event_id: str) -> Row | None: ...

    async def insert_event(self, payload: Row) -> Row: ...

    async def update_event(self, event_id: str, fields: Row) -> Row: ...

    async def delete_event(self, event_id: str) -> bool: ...

    async def list_projects_by_ids(self, project_ids: list[str]) -> list[Row]: ...

    async def list_members_by_ids(self, member_ids: list[str]) -> list[Row]: ...


class SupabaseCalendarRepository:
    """PostgREST-backed repository (service role client, so RLS does not apply)."""

    async def _run(self, operation):
        try:
            return await run_in_threadpool(operation)
        except APIError as exc:
            raise CalendarRequestError(_describe_api_error(exc)) from exc

    async def list_personal_events(
        self, *, member_id: str, start: datetime, end: datetime
    ) -> list[Row]:
        def run() -> list[Row]:
            response = (
                admin_client()
                .table("calendar_events")
                .select("*")
                .eq("member_id", member_id)
                .is_("project_id", "null")
                .gte("starts_at", start.isoformat())
                .lte("starts_at", end.isoformat())
                .order("starts_at")
                .execute()
            )
            return response.data or []

        return await self._run(run)

    async def list_project_events(
        self, *, project_ids: list[str], start: datetime, end: datetime
    ) -> list[Row]:
        if not project_ids:
            return []

        def run() -> list[Row]:
            response = (
                admin_client()
                .table("calendar_events")
                .select("*")
                .in_("project_id", project_ids)
                .gte("starts_at", start.isoformat())
                .lte("starts_at", end.isoformat())
                .order("starts_at")
                .execute()
            )
            return response.data or []

        return await self._run(run)

    async def get_event(self, event_id: str) -> Row | None:
        def run() -> Row | None:
            response = (
                admin_client()
                .table("calendar_events")
                .select("*")
                .eq("id", event_id)
                .limit(1)
                .execute()
            )
            rows = response.data or []
            return dict(rows[0]) if rows else None

        return await self._run(run)

    async def insert_event(self, payload: Row) -> Row:
        def run() -> Row:
            response = admin_client().table("calendar_events").insert(payload).execute()
            return dict(response.data[0])

        return await self._run(run)

    async def update_event(self, event_id: str, fields: Row) -> Row:
        def run() -> Row:
            response = (
                admin_client().table("calendar_events").update(fields).eq("id", event_id).execute()
            )
            return dict(response.data[0])

        return await self._run(run)

    async def delete_event(self, event_id: str) -> bool:
        def run() -> bool:
            response = admin_client().table("calendar_events").delete().eq("id", event_id).execute()
            return bool(response.data)

        return await self._run(run)

    async def list_projects_by_ids(self, project_ids: list[str]) -> list[Row]:
        if not project_ids:
            return []

        def run() -> list[Row]:
            response = (
                admin_client().table("projects").select("id, name").in_("id", project_ids).execute()
            )
            return response.data or []

        return await self._run(run)

    async def list_members_by_ids(self, member_ids: list[str]) -> list[Row]:
        if not member_ids:
            return []

        def run() -> list[Row]:
            response = (
                admin_client()
                .table("members")
                .select("id, display_name")
                .in_("id", member_ids)
                .execute()
            )
            return response.data or []

        return await self._run(run)
