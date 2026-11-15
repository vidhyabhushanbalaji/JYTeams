"""The public surface of Graph AI Search — the only module another section may import.

The tickets section reuses this walk to find the documents a ticket is about. Everything else
here (repository, scorer, reader, storage) stays internal to the section.
"""

from __future__ import annotations

from app.core.access import ProjectAccess
from app.core.config import Settings
from app.graph_ai_search.repository import SupabaseSearchRepository
from app.graph_ai_search.scoring import LocalScorer
from app.graph_ai_search.service import DEFAULT_LIMIT, GraphSearchService
from app.graph_ai_search.storage import DocumentTextReader, build_reader

#: The scorer is stateless, so one instance serves every caller.
_SCORER = LocalScorer()
#: The reader owns the digest cache — it must outlive a request to be worth having.
_READER: DocumentTextReader | None = None


def _reader_for(settings: Settings) -> DocumentTextReader:
    """Create the document reader once per process (its cache is the point)."""
    global _READER
    if _READER is None:
        _READER = build_reader(
            cache_entries=settings.blob_cache_entries,
            max_chars=settings.search_max_document_chars,
        )
    return _READER


def build_service(settings: Settings, *, access: ProjectAccess | None = None) -> GraphSearchService:
    """Wire a search service (Supabase repository, shared reader, local scorer)."""
    return GraphSearchService(
        repository=SupabaseSearchRepository(),
        reader=_reader_for(settings),
        scorer=_SCORER,
        settings=settings,
        access=access,
    )


async def search_project(
    service: GraphSearchService,
    *,
    project_id: str,
    member_id: str,
    query: str,
    context: str = "",
    limit: int = DEFAULT_LIMIT,
) -> dict:
    """Run one search and return the response body as a plain dict.

    Read-only and model-free: the walk is local, and the cache it uses is keyed by content
    digest. ``limit`` is clamped by the service (and validated there).
    """
    return await service.search(
        project_id=project_id,
        owner_id=member_id,
        query=query,
        context=context,
        limit=limit,
    )
