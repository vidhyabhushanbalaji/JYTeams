"""Persistence for the Graph Creation section.

The protocol keeps the service testable (tests use an in-memory repository); the
Supabase implementation is a thin PostgREST wrapper and does no business logic.
"""

from __future__ import annotations

from typing import Any, Protocol

from fastapi import HTTPException, status
from postgrest.exceptions import APIError
from starlette.concurrency import run_in_threadpool

from app.db.supabase import admin_client

Row = dict[str, Any]

_INSERT_BATCH = 500


class SupabaseRequestError(HTTPException):
    """Supabase/PostgREST rejected a request (API key, RLS policy or schema problem)."""

    def __init__(self, message: str) -> None:
        super().__init__(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=message)


def _describe_api_error(exc: APIError) -> str:
    """Turn a PostgREST error into something that says what to fix."""
    message = str(getattr(exc, "message", None) or exc)
    code = getattr(exc, "code", None)
    if code == "42501":
        message += (
            " - the request ran without service-role privileges; check that"
            " SUPABASE_SERVICE_ROLE_KEY holds the secret key (sb_secret_...) and not"
            " the publishable key, then restart the API"
        )
    elif code == "23503":
        message += (
            " - a referenced row is missing; in AUTH_MODE=dev the owner id must be a"
            " real Supabase user, so set DEV_USER_ID to that user's UUID"
            " (Authentication -> Users) and restart the API"
        )
    elif code == "23505":
        message += " - that path or name already exists in this project"
    if getattr(exc, "hint", None):
        message += f" (hint: {exc.hint})"
    return f"Supabase rejected the request: {message}"


class GraphRepository(Protocol):
    """Data access used by :class:`app.graph_creation.service.GraphCreationService`."""

    async def create_project(self, *, owner_id: str, name: str) -> Row: ...

    async def update_project(self, project_id: str, fields: Row) -> Row: ...

    async def get_project(self, project_id: str) -> Row | None: ...

    async def list_projects(self, owner_id: str) -> list[Row]: ...

    async def create_job(
        self, *, project_id: str, owner_id: str, mode: str, total_files: int
    ) -> Row: ...

    async def update_job(self, job_id: str, fields: Row) -> Row: ...

    async def get_job(self, job_id: str) -> Row | None: ...

    async def insert_directories(self, rows: list[Row]) -> list[Row]: ...

    async def insert_files(self, rows: list[Row]) -> list[Row]: ...

    async def update_directory(self, directory_id: str, fields: Row) -> Row: ...

    async def get_directory(self, directory_id: str) -> Row | None: ...

    async def list_directories(self, project_id: str) -> list[Row]: ...

    async def list_files(self, project_id: str) -> list[Row]: ...


class SupabaseGraphRepository:
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

    async def create_project(self, *, owner_id: str, name: str) -> Row:
        def run() -> Row:
            builder = admin_client().table("projects").insert({"owner_id": owner_id, "name": name})
            response = builder.execute()
            return response.data[0]

        return await self._run(run)

    async def update_project(self, project_id: str, fields: Row) -> Row:
        def run() -> Row:
            builder = admin_client().table("projects").update(fields).eq("id", project_id)
            response = builder.execute()
            return response.data[0]

        return await self._run(run)

    async def get_project(self, project_id: str) -> Row | None:
        return await self._one(
            lambda: admin_client().table("projects").select("*").eq("id", project_id).limit(1)
        )

    async def list_projects(self, owner_id: str) -> list[Row]:
        def run() -> list[Row]:
            response = (
                admin_client()
                .table("projects")
                .select("*")
                .eq("owner_id", owner_id)
                .order("created_at", desc=True)
                .execute()
            )
            return response.data or []

        return await self._run(run)

    async def create_job(
        self, *, project_id: str, owner_id: str, mode: str, total_files: int
    ) -> Row:
        payload = {
            "project_id": project_id,
            "owner_id": owner_id,
            "mode": mode,
            "total_files": total_files,
            "status": "queued",
        }

        def run() -> Row:
            response = admin_client().table("creation_jobs").insert(payload).execute()
            return response.data[0]

        return await self._run(run)

    async def update_job(self, job_id: str, fields: Row) -> Row:
        def run() -> Row:
            response = (
                admin_client().table("creation_jobs").update(fields).eq("id", job_id).execute()
            )
            return response.data[0]

        return await self._run(run)

    async def get_job(self, job_id: str) -> Row | None:
        return await self._one(
            lambda: admin_client().table("creation_jobs").select("*").eq("id", job_id).limit(1)
        )

    async def _insert(self, table: str, rows: list[Row]) -> list[Row]:
        inserted: list[Row] = []
        for start in range(0, len(rows), _INSERT_BATCH):
            chunk = rows[start : start + _INSERT_BATCH]

            def run(batch: list[Row] = chunk) -> list[Row]:
                response = admin_client().table(table).insert(batch).execute()
                return response.data or []

            inserted.extend(await self._run(run))
        return inserted

    async def insert_directories(self, rows: list[Row]) -> list[Row]:
        return await self._insert("directories", rows)

    async def insert_files(self, rows: list[Row]) -> list[Row]:
        return await self._insert("files", rows)

    async def update_directory(self, directory_id: str, fields: Row) -> Row:
        def run() -> Row:
            response = (
                admin_client().table("directories").update(fields).eq("id", directory_id).execute()
            )
            return response.data[0]

        return await self._run(run)

    async def get_directory(self, directory_id: str) -> Row | None:
        return await self._one(
            lambda: admin_client().table("directories").select("*").eq("id", directory_id).limit(1)
        )

    async def list_directories(self, project_id: str) -> list[Row]:
        def run() -> list[Row]:
            builder = admin_client().table("directories").select("*").eq("project_id", project_id)
            response = builder.execute()
            return response.data or []

        return await self._run(run)

    async def list_files(self, project_id: str) -> list[Row]:
        def run() -> list[Row]:
            response = (
                admin_client().table("files").select("*").eq("project_id", project_id).execute()
            )
            return response.data or []

        return await self._run(run)
