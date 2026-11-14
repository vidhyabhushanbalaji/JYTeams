"""Response models for the Graph AI Search section."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SearchHit(BaseModel):
    """One document that answers the query, with the evidence that got it there."""

    file_id: str
    name: str
    path: str
    directory_id: str
    directory_path: str
    score: float
    #: Query terms found in the document (or its name), so the score is explainable.
    matched_terms: list[str] = Field(default_factory=list)
    #: A snippet around the first match — no model summarised it, so it is always faithful.
    excerpt: str = ""


class DirectoryHit(BaseModel):
    """A folder worth browsing, judged from its stored description."""

    directory_id: str
    path: str
    name: str
    depth: int
    score: float
    matched_terms: list[str] = Field(default_factory=list)


class SearchTraversal(BaseModel):
    """What the walk cost, and whether it had to improvise."""

    directories_visited: int
    directories_opened: int
    documents_considered: int
    #: Documents whose stored text was actually read (the expensive part of a search).
    files_read: int
    fallback_used: bool
    degraded: bool
    budget_exhausted: bool
    #: Identifies the scorer that produced the ordering (see ``ScoreConfig.version``).
    scorer_version: str
    duration_ms: int


class SearchResults(BaseModel):
    """The ranked answers to one query."""

    query: str
    context: str = ""
    project_id: str
    results: list[SearchHit] = Field(default_factory=list)
    #: Folders whose descriptions matched, so a client can offer "browse this instead".
    directories: list[DirectoryHit] = Field(default_factory=list)
    #: Paths whose documents were read (``""`` is the project root).
    opened_directories: list[str] = Field(default_factory=list)
    traversal: SearchTraversal
