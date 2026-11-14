"""Persistence for the Graph Add section.

Same shape as the rest of the backend: a narrow protocol the service depends on, and a thin
PostgREST implementation that carries no business logic. The protocol keeps the service
testable against an in-memory repository.
"""

from __future__ import annotations

from typing import Any, Protocol

from fastapi import HTTPException, status
from postgrest.exceptions import APIError
from starlette.concurrency import run_in_threadpool

from app.db.supabase import admin_client

Row = dict[str, Any]

_RLS_CODE = "42501"


class SupabaseRequestError(HTTPException):
    """Supabase/PostgREST rejected a request (API key, RLS policy or schema problem)."""

    def __init__(self, message: str) -> None:
        super().__init__(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=message)


def _describe_api_error(exc: APIError) -> str:
    """Turn a PostgREST error into something that says what to fix."""
    message = str(getattr(exc, "message", None) or exc)
    if getattr(exc, "code", None) == _RLS_CODE:
        message += (
            " - the request ran without service-role privileges; check that"
            " SUPABASE_SERVICE_ROLE_KEY holds the secret key (sb_secret_...) and not"
            " the publishable key, then restart the API"
        )
    if getattr(exc, "hint", None):
        message += f" (hint: {exc.hint})"
    return f"Supabase rejected the request: {message}"


class AddRepository(Protocol):
    """Data access used by :class:`app.graph_add.service.GraphAddService`."""

    async def get_project(self, project_id: str) -> Row | None: ...

    async def update_project(self, project_id: str, fields: Row) -> Row: ...

    async def list_directories(self, project_id: str) -> list[Row]: ...

    async def list_files(self, project_id: str) -> list[Row]: ...

    async def insert_directory(self, row: Row) -> Row: ...

    async def insert_file(self, row: Row) -> Row: ...

    async def update_directory(self, directory_id: str, fields: Row) -> Row: ...

    async def create_add_request(self, row: Row) -> Row: ...

    async def get_add_request(self, request_id: str) -> Row | None: ...

    async def update_add_request(self, request_id: str, fields: Row) -> Row: ...


class SupabaseAddRepository:
    """PostgREST-backed repository (service role client, so RLS does not apply)."""

    async def _run(self, operation):
        """Run a blocking PostgREST call, surfacing Supabase errors as HTTP errors."""
        try:
            return await run_in_threadpool(operation)
        except APIError as exc:
            raise SupabaseRequestError(_describe_api_error(exc)) from exc

    async def _one(self, builder_factory: Any) -> Row | None:
        def run() -> Row | None:
            response = builder_factory().execute()
            return response.data[0] if response.data else None

        return await self._run(run)

    async def _insert(self, table: str, payload: Row) -> Row:
        def run() -> Row:
            response = admin_client().table(table).insert(payload).execute()
            if not response.data:
                raise SupabaseRequestError(f"Supabase returned no row for the {table} insert")
            return response.data[0]

        return await self._run(run)

    async def _update(self, table: str, row_id: str, fields: Row) -> Row:
        def run() -> Row:
            response = admin_client().table(table).update(fields).eq("id", row_id).execute()
            if not response.data:
                raise SupabaseRequestError(f"Supabase returned no row for the {table} update")
            return response.data[0]

        return await self._run(run)

    async def get_project(self, project_id: str) -> Row | None:
        return await self._one(
            lambda: admin_client().table("projects").select("*").eq("id", project_id).limit(1)
        )

    async def update_project(self, project_id: str, fields: Row) -> Row:
        return await self._update("projects", project_id, fields)

    async def list_directories(self, project_id: str) -> list[Row]:
        def run() -> list[Row]:
            response = (
                admin_client()
                .table("directories")
                .select("*")
                .eq("project_id", project_id)
                .execute()
            )
            return response.data or []

        return await self._run(run)

    async def list_files(self, project_id: str) -> list[Row]:
        def run() -> list[Row]:
            response = (
                admin_client().table("files").select("*").eq("project_id", project_id).execute()
            )
            return response.data or []

        return await self._run(run)

    async def insert_directory(self, row: Row) -> Row:
        return await self._insert("directories", row)

    async def insert_file(self, row: Row) -> Row:
        return await self._insert("files", row)

    async def update_directory(self, directory_id: str, fields: Row) -> Row:
        return await self._update("directories", directory_id, fields)

    async def create_add_request(self, row: Row) -> Row:
        return await self._insert("add_requests", row)

    async def get_add_request(self, request_id: str) -> Row | None:
        return await self._one(
            lambda: admin_client().table("add_requests").select("*").eq("id", request_id).limit(1)
        )

    async def update_add_request(self, request_id: str, fields: Row) -> Row:
        return await self._update("add_requests", request_id, fields)
