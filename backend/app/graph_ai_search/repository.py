"""Read-only persistence for the Graph AI Search section.

Search never writes: it needs the project (for the ownership check) and the tree rows that
hold the summaries and descriptions. The protocol keeps the service testable against an
in-memory repository.
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


class SearchRepository(Protocol):
    """Data access used by :class:`app.graph_ai_search.service.GraphSearchService`."""

    async def get_project(self, project_id: str) -> Row | None: ...

    async def list_directories(self, project_id: str) -> list[Row]: ...

    async def list_files(self, project_id: str) -> list[Row]: ...


class SupabaseSearchRepository:
    """PostgREST-backed read-only repository (service role client)."""

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

    async def get_project(self, project_id: str) -> Row | None:
        return await self._one(
            lambda: admin_client().table("projects").select("*").eq("id", project_id).limit(1)
        )

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
