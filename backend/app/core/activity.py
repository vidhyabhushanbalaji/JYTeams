"""The activity feed's write side, shared by the sections that move project content.

Tickets log their own events; Graph Creation (an upload finishing, a document saved) and Graph
Add (a placement) log project-level events through this port, so the tickets page can show
"what changed" even when nothing touched a ticket.

Recording is best effort on purpose: an audit row must never fail an upload or a placement, so
:class:`SupabaseActivityLog` swallows and logs its own errors. Sections take the log as an
injected dependency whose default is a no-op, which keeps their unit tests hermetic.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any

from starlette.concurrency import run_in_threadpool

from app.db.supabase import admin_client

logger = logging.getLogger(__name__)

#: Event kinds written by the tickets section and by the sections that change project content.
TICKET_CREATED = "ticket_created"
TICKET_ASSIGNED = "ticket_assigned"
TICKET_STATUS_CHANGED = "ticket_status_changed"
TICKET_COMPLETED = "ticket_completed"
TICKET_REOPENED = "ticket_reopened"
TICKET_UPDATED = "ticket_updated"
TICKET_COMMENTED = "ticket_commented"
FILE_ATTACHED = "file_attached"
FILE_DETACHED = "file_detached"
PROJECT_SHARED = "project_shared"
PROJECT_MEMBER_REMOVED = "project_member_removed"
FILES_UPLOADED = "files_uploaded"
FILE_ADDED = "file_added"
DOCUMENT_SAVED = "document_saved"


class ActivityLog(ABC):
    """Append one event to a project's feed."""

    @abstractmethod
    async def record(
        self,
        *,
        project_id: str,
        member_id: str | None,
        kind: str,
        detail: Mapping[str, Any] | None = None,
        ticket_id: str | None = None,
    ) -> None:
        """Write one event. Implementations must not raise."""


class NoopActivityLog(ActivityLog):
    """The default: sections that were not wired with a log simply record nothing."""

    async def record(
        self,
        *,
        project_id: str,
        member_id: str | None,
        kind: str,
        detail: Mapping[str, Any] | None = None,
        ticket_id: str | None = None,
    ) -> None:
        return None


NOOP: ActivityLog = NoopActivityLog()


class SupabaseActivityLog(ActivityLog):
    """Writes ``ticket_events``. A failure is logged and dropped, never raised."""

    async def record(
        self,
        *,
        project_id: str,
        member_id: str | None,
        kind: str,
        detail: Mapping[str, Any] | None = None,
        ticket_id: str | None = None,
    ) -> None:
        payload = {
            "project_id": project_id,
            "ticket_id": ticket_id,
            "member_id": member_id,
            "kind": kind,
            "detail": dict(detail or {}),
        }
        try:
            await run_in_threadpool(
                lambda: admin_client().table("ticket_events").insert(payload).execute()
            )
        except Exception:  # noqa: BLE001 - an audit row must not break the real work
            logger.warning("Could not record activity %s for project %s", kind, project_id)
            logger.debug("Activity write failed", exc_info=True)
