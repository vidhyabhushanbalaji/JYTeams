"""Contract and validation of the search service against in-memory collaborators."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.core.config import get_settings
from app.graph_ai_search.service import MAX_LIMIT, GraphSearchService
from app.graph_ai_search.tests.fakes import InMemorySearchRepository, ScriptedSearcher

PULSE = {
    "": {
        "files": ["README.md"],
        "folders": ["docs", "guides"],
    },
    "docs": {"files": ["api-reference.md", "architecture.md"], "folders": []},
    "guides": {"files": ["deployment.md"], "folders": []},
}
RANKING = ["deployment.md", "api-reference.md", "architecture.md", "README.md"]


def _service(searcher: ScriptedSearcher | None = None):
    repository = InMemorySearchRepository()
    service = GraphSearchService(
        repository=repository,
        searcher=searcher or ScriptedSearcher(matches=PULSE, ranking=RANKING),
        settings=get_settings(),
    )
    return service, repository


def _seed(repository: InMemorySearchRepository):
    project = repository.seed_project()
    root_id = project["root_directory_id"]
    repository.seed_file(
        project["id"], directory_id=root_id, name="README.md", summary="PulseAPI overview."
    )
    docs = repository.seed_directory(
        project["id"], parent_id=root_id, name="docs", description="API and architecture."
    )
    repository.seed_file(
        project["id"], directory_id=docs["id"], name="api-reference.md", summary="Endpoints."
    )
    repository.seed_file(
        project["id"],
        directory_id=docs["id"],
        name="architecture.md",
        summary="Ingestion pipeline design.",
    )
    guides = repository.seed_directory(
        project["id"], parent_id=root_id, name="guides", description="Deployment instructions."
    )
    repository.seed_file(
        project["id"],
        directory_id=guides["id"],
        name="deployment.md",
        summary="Helm deployment steps.",
    )
    return project


async def _search(service, project, **kwargs):
    return await service.search(
        project_id=project["id"],
        owner_id="user-1",
        query=kwargs.pop("query", "how do I deploy a release"),
        **kwargs,
    )


async def test_search_returns_the_ranked_hits() -> None:
    service, repository = _service()
    project = _seed(repository)

    payload = await _search(service, project)

    assert set(payload) == {
        "query",
        "project_id",
        "results",
        "opened_directories",
        "traversal",
    }
    assert [hit["name"] for hit in payload["results"]] == RANKING
    top = payload["results"][0]
    assert set(top) == {
        "file_id",
        "name",
        "path",
        "directory_id",
        "directory_path",
        "summary",
        "score",
        "reason",
    }
    assert top["path"] == "guides/deployment.md"
    assert top["directory_path"] == "guides"
    assert top["score"] > 0
    assert payload["opened_directories"] == ["", "docs", "guides"]
    assert payload["traversal"]["model"] == "scripted"
    assert payload["traversal"]["fallback_used"] is False
    assert payload["traversal"]["degraded"] is False


async def test_limit_and_min_score_trim_the_results() -> None:
    service, repository = _service()
    project = _seed(repository)

    limited = await _search(service, project, limit=2)
    filtered = await _search(service, project, min_score=0.95)

    assert len(limited["results"]) == 2
    assert all(hit["score"] >= 0.95 for hit in filtered["results"])


async def test_a_short_query_is_rejected() -> None:
    service, repository = _service()
    project = _seed(repository)

    with pytest.raises(HTTPException) as excinfo:
        await _search(service, project, query="  ab  ")

    assert excinfo.value.status_code == 400
    assert "at least" in str(excinfo.value.detail)


async def test_an_over_long_query_is_rejected() -> None:
    service, repository = _service()
    project = _seed(repository)

    with pytest.raises(HTTPException) as excinfo:
        await _search(service, project, query="x" * 501)

    assert excinfo.value.status_code == 400


@pytest.mark.parametrize("limit", [0, MAX_LIMIT + 1])
async def test_limit_bounds_are_enforced(limit: int) -> None:
    service, repository = _service()
    project = _seed(repository)

    with pytest.raises(HTTPException) as excinfo:
        await _search(service, project, limit=limit)

    assert excinfo.value.status_code == 400


async def test_other_numeric_bounds_are_enforced() -> None:
    service, repository = _service()
    project = _seed(repository)

    with pytest.raises(HTTPException):
        await _search(service, project, min_score=1.5)
    with pytest.raises(HTTPException):
        await _search(service, project, max_directories=0)


async def test_another_users_project_is_not_found() -> None:
    service, repository = _service()
    project = _seed(repository)

    with pytest.raises(HTTPException) as excinfo:
        await service.search(project_id=project["id"], owner_id="someone-else", query="deployment")

    assert excinfo.value.status_code == 404


async def test_a_project_without_a_tree_is_a_conflict() -> None:
    service, repository = _service()
    empty = repository.seed_project()
    repository.directories.clear()
    repository.projects[empty["id"]]["owner_id"] = "user-1"

    with pytest.raises(HTTPException) as excinfo:
        await _search(service, empty)

    assert excinfo.value.status_code == 409


async def test_a_degraded_walk_is_reported_not_raised() -> None:
    service, repository = _service(ScriptedSearcher(fail_judging=True))
    project = _seed(repository)

    payload = await _search(service, project)

    assert payload["results"] == []
    assert payload["traversal"]["degraded"] is True
