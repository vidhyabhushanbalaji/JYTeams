"""Response models for the Graph AI Search section."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SearchHit(BaseModel):
    """One document the search believes answers the query."""

    file_id: str
    name: str
    path: str
    directory_id: str
    directory_path: str
    summary: str
    score: float
    reason: str


class SearchTraversal(BaseModel):
    """What the walk cost, and whether it had to improvise."""

    directories_visited: int
    directories_opened: int
    documents_considered: int
    fallback_used: bool
    degraded: bool
    budget_exhausted: bool
    model: str


class SearchResults(BaseModel):
    """The ranked answers to one query."""

    query: str
    project_id: str
    results: list[SearchHit] = Field(default_factory=list)
    #: Paths whose contents were actually read (``""`` is the project root).
    opened_directories: list[str] = Field(default_factory=list)
    traversal: SearchTraversal
