"""Adapters between the tickets section and the sections it reuses.

A section may not import another section's internals, so both edges go through the other
section's documented public module:
:mod:`app.graph_ai_search.public` (the walk that finds a ticket's files) and, from the client,
Graph Add's HTTP suggestion endpoint (the placement wizard).
"""

from __future__ import annotations

from typing import Any

from app.core.access import SupabaseProjectAccess
from app.core.config import Settings
from app.graph_ai_search import public as search_section


class GraphSearchAdapter:
    """Implements :class:`app.tickets.service.TicketSearch` with Graph AI Search."""

    def __init__(self, settings: Settings) -> None:
        self._service = search_section.build_service(settings, access=SupabaseProjectAccess())

    async def search(
        self,
        *,
        project_id: str,
        member_id: str,
        query: str,
        context: str,
        limit: int,
    ) -> dict[str, Any]:
        return await search_section.search_project(
            self._service,
            project_id=project_id,
            member_id=member_id,
            query=query,
            context=context,
            limit=limit,
        )
