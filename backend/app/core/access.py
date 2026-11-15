"""Project access, shared by every section.

A project belongs to the members listed in ``project_members``; ``projects.owner_id`` is only
the creator (it keeps the "owner" role). The backend uses the service-role client, which
bypasses row level security, so membership is enforced here and every section asks this object
instead of comparing ``owner_id`` itself.

A missing project and a project the caller is not a member of both answer **404**: whether a
project exists is not something a stranger gets to learn.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from enum import StrEnum

from fastapi import HTTPException, status
from postgrest.exceptions import APIError
from starlette.concurrency import run_in_threadpool

from app.db.supabase import admin_client

logger = logging.getLogger(__name__)


class ProjectRole(StrEnum):
    """What a member may do in a project."""

    OWNER = "owner"
    MEMBER = "member"


class ProjectAccess(ABC):
    """The membership question every section needs answered."""

    @abstractmethod
    async def role(self, project_id: str, member_id: str) -> ProjectRole | None:
        """The caller's role in the project, or ``None`` when they are not a member."""

    @abstractmethod
    async def project_ids(self, member_id: str) -> list[str]:
        """Every project the member can see (owned or shared with them)."""

    async def require(self, project_id: str, member_id: str) -> ProjectRole:
        """The caller's role, or 404 — used by services before touching a project."""
        role = await self.role(project_id, member_id)
        if role is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
        return role


class SupabaseProjectAccess(ProjectAccess):
    """Membership read from ``project_members`` (service role, so RLS does not apply)."""

    async def _run(self, operation):
        try:
            return await run_in_threadpool(operation)
        except APIError as exc:
            logger.exception("Could not read project membership")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Supabase rejected the membership check: {getattr(exc, 'message', exc)}",
            ) from exc

    async def role(self, project_id: str, member_id: str) -> ProjectRole | None:
        def run() -> str | None:
            response = (
                admin_client()
                .table("project_members")
                .select("role")
                .eq("project_id", project_id)
                .eq("member_id", member_id)
                .limit(1)
                .execute()
            )
            rows = response.data or []
            return rows[0].get("role") if rows else None

        value = await self._run(run)
        return ProjectRole(value) if value in {"owner", "member"} else None

    async def project_ids(self, member_id: str) -> list[str]:
        def run() -> list[str]:
            response = (
                admin_client()
                .table("project_members")
                .select("project_id")
                .eq("member_id", member_id)
                .execute()
            )
            return [str(row["project_id"]) for row in (response.data or [])]

        return await self._run(run)
