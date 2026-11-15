"""HTTP routes for the Graph AI Search section.

Mounted at ``/api/graph-ai-search``. One endpoint: a read that walks the project tree for a query
and returns the documents that answer it, ranked, plus the folders worth browsing. Nothing is
written and no model is called, so it is safe to call repeatedly.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.access import SupabaseProjectAccess
from app.core.auth import CurrentUser, get_current_user
from app.core.config import get_settings
from app.graph_ai_search.public import build_service
from app.graph_ai_search.schemas import SearchResults
from app.graph_ai_search.service import GraphSearchService

router = APIRouter(tags=["Graph AI Search"])


def get_service() -> GraphSearchService:
    """Wire the service for a request (Supabase repository, shared reader, local scorer)."""
    return build_service(get_settings(), access=SupabaseProjectAccess())


ServiceDep = Annotated[GraphSearchService, Depends(get_service)]
UserDep = Annotated[CurrentUser, Depends(get_current_user)]


@router.get(
    "/projects/{project_id}/search",
    response_model=SearchResults,
    summary="Search a project tree for the documents that answer a query",
)
async def search_project(
    project_id: str,
    user: UserDep,
    service: ServiceDep,
    q: Annotated[str, Query(description="What you are looking for")],
    context: Annotated[
        str,
        Query(
            description=(
                "Optional extra context to widen the match (for example the surrounding "
                "sentence, or a synonym the query missed)."
            )
        ),
    ] = "",
    limit: Annotated[int, Query(description="Maximum results to return")] = 8,
    min_score: Annotated[float, Query(description="Drop results below this score (0.0-1.0)")] = 0.0,
    max_directories: Annotated[
        int | None,
        Query(
            description=(
                "Optional valve: stop after opening this many folders. Omit for an "
                "exhaustive walk of every matching branch."
            )
        ),
    ] = None,
) -> SearchResults:
    result = await service.search(
        project_id=project_id,
        owner_id=user.id,
        query=q,
        context=context,
        limit=limit,
        min_score=min_score,
        max_directories=max_directories,
    )
    return SearchResults(**result)
