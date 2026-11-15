"""Persistence for the Chat section.

The protocol keeps the service testable (the tests use an in-memory repository); the Supabase
implementation is a thin PostgREST wrapper and does no business logic. Membership is *not*
checked here — that is :class:`app.core.access.ProjectAccess`.
"""

from __future__ import annotations

from typing import Any, Protocol

from fastapi import HTTPException, status
from postgrest.exceptions import APIError
from starlette.concurrency import run_in_threadpool

from app.db.supabase import admin_client

Row = dict[str, Any]


class ChatRequestError(HTTPException):
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
            " - a referenced row is missing; apply supabase/migrations/0005_chat.sql and make"
            " sure the member id comes from POST /api/tickets/members"
        )
    if getattr(exc, "hint", None):
        message += f" (hint: {exc.hint})"
    return f"Supabase rejected the request: {message}"


class ChatRepository(Protocol):
    """Data access used by :class:`app.chat.service.ChatService`."""

    async def insert_message(self, payload: Row) -> Row: ...

    async def get_message(self, message_id: str) -> Row | None: ...

    async def list_messages(
        self, *, project_id: str, after_seq: int | None = None, limit: int = 50
    ) -> list[Row]: ...

    async def latest_message(self, project_id: str) -> Row | None: ...

    async def update_message(self, message_id: str, fields: Row) -> Row: ...

    async def list_projects_by_ids(self, project_ids: list[str]) -> list[Row]: ...

    async def list_members_by_ids(self, member_ids: list[str]) -> list[Row]: ...


class SupabaseChatRepository:
    """PostgREST-backed repository (service role client, so RLS does not apply)."""

    async def _run(self, operation):
        try:
            return await run_in_threadpool(operation)
        except APIError as exc:
            raise ChatRequestError(_describe_api_error(exc)) from exc

    async def _one(self, builder_factory) -> Row | None:
        response = await self._run(lambda: builder_factory().limit(1).execute())
        rows = response.data or []
        return dict(rows[0]) if rows else None

    async def insert_message(self, payload: Row) -> Row:
        def run() -> Row:
            response = admin_client().table("chat_messages").insert(payload).execute()
            return dict(response.data[0])

        return await self._run(run)

    async def get_message(self, message_id: str) -> Row | None:
        return await self._one(
            lambda: admin_client().table("chat_messages").select("*").eq("id", message_id)
        )

    async def list_messages(
        self, *, project_id: str, after_seq: int | None = None, limit: int = 50
    ) -> list[Row]:
        """The newest ``limit`` messages of one project, oldest first.

        With ``after_seq`` this is the poll: everything newer than the cursor, ascending.
        Without it, the page is taken newest-first and reversed, so callers always receive
        chronological order.
        """

        def run() -> list[Row]:
            builder = admin_client().table("chat_messages").select("*").eq("project_id", project_id)
            if after_seq is not None:
                response = builder.gt("seq", after_seq).order("seq").limit(limit).execute()
                return response.data or []
            response = builder.order("seq", desc=True).limit(limit).execute()
            return list(reversed(response.data or []))

        return await self._run(run)

    async def latest_message(self, project_id: str) -> Row | None:
        def run() -> Row | None:
            response = (
                admin_client()
                .table("chat_messages")
                .select("*")
                .eq("project_id", project_id)
                .order("seq", desc=True)
                .limit(1)
                .execute()
            )
            rows = response.data or []
            return dict(rows[0]) if rows else None

        return await self._run(run)

    async def update_message(self, message_id: str, fields: Row) -> Row:
        def run() -> Row:
            response = (
                admin_client().table("chat_messages").update(fields).eq("id", message_id).execute()
            )
            return dict(response.data[0])

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
