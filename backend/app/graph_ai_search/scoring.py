"""Local scoring for Graph AI Search: folder relevance and document relevance, no model calls.

The algorithm lives in :mod:`app.core.text` so Graph Add ranks folders identically. This module
only adapts the section's briefs to it and keeps the tuning knobs in one place.
"""

from __future__ import annotations

from app.core.text import Query, ScoreConfig, score_document_texts, score_folder_texts, terms
from app.graph_ai_search.search import DocumentBrief, DocumentScore, FolderBrief, FolderScore


class LocalScorer:
    """Deterministic scorer shared by every search in the process."""

    def __init__(self, *, config: ScoreConfig | None = None) -> None:
        self._config = config or ScoreConfig()

    @property
    def version(self) -> str:
        return self._config.version

    def score_folder(self, query: Query, folder: FolderBrief) -> FolderScore:
        """How plausibly ``folder`` (or something under it) answers ``query``."""
        score = score_folder_texts(
            query,
            name=folder.name,
            description=folder.description,
            contains=folder.contains,
            config=self._config,
        )
        haystack = terms(f"{folder.name} {folder.description} {' '.join(folder.contains)}")
        return FolderScore(score=score, matched=query.matched(haystack))

    def score_document(self, query: Query, document: DocumentBrief, body: str) -> DocumentScore:
        """How well one document answers ``query``, judged from its own text."""
        score = score_document_texts(query, name=document.name, body=body, config=self._config)
        return DocumentScore(score=score, matched=query.matched(terms(body) | terms(document.name)))
