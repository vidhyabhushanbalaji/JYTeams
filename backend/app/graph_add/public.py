"""The public surface of Graph Add — the only module another section may import.

The tickets section offers the placement wizard for a ticket's file, passing the ticket's own
words as ``context``. Everything else (repository, navigator, describer, storage) stays internal.
"""

from __future__ import annotations

from app.core.access import ProjectAccess
from app.core.activity import NOOP, ActivityLog
from app.core.config import Settings
from app.graph_add.describer import build_describer
from app.graph_add.repository import SupabaseAddRepository
from app.graph_add.service import GraphAddService
from app.graph_add.storage import SupabaseObjectStore


def build_service(
    settings: Settings,
    *,
    access: ProjectAccess | None = None,
    activity: ActivityLog = NOOP,
) -> GraphAddService:
    """Wire an add service (Supabase repository + storage + folder describer)."""
    return GraphAddService(
        repository=SupabaseAddRepository(),
        store=SupabaseObjectStore(bucket=settings.storage_bucket),
        describer=build_describer(settings),
        settings=settings,
        access=access,
        activity=activity,
    )


async def suggest_document(
    service: GraphAddService,
    *,
    member_id: str,
    project_id: str,
    filename: str,
    data: bytes,
    context: str = "",
) -> dict:
    """Rank the folders one document could join, with optional surrounding context."""
    return await service.suggest(
        owner_id=member_id,
        project_id=project_id,
        filename=filename,
        data=data,
        context=context,
    )
