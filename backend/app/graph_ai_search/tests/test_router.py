"""HTTP contract of the Graph AI Search route (in-memory repository, no network)."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.graph_ai_search.router import get_service
from app.graph_ai_search.service import GraphSearchService
from app.graph_ai_search.tests.fakes import InMemorySearchRepository, ScriptedSearcher
from app.main import create_app

SEARCH = "/api/graph-ai-search/projects/{project_id}/search"

MATCHES = {
    "": {"files": ["README.md"], "folders": ["guides"]},
    "guides": {"files": ["deployment.md"], "folders": []},
}


@pytest.fixture()
def repository() -> InMemorySearchRepository:
    return InMemorySearchRepository()


@pytest.fixture()
def seeded(repository: InMemorySearchRepository):
    project = repository.seed_project(owner_id="user-1")
    root_id = project["root_directory_id"]
    repository.seed_file(
        project["id"], directory_id=root_id, name="README.md", summary="Project overview."
    )
    guides = repository.seed_directory(
        project["id"],
        parent_id=root_id,
        name="guides",
        description="Deployment and rollback procedures.",
    )
    repository.seed_file(
        project["id"],
        directory_id=guides["id"],
        name="deployment.md",
        summary="Helm deployment steps.",
    )
    return project


@pytest.fixture()
def api(repository: InMemorySearchRepository) -> Iterator[TestClient]:
    service = GraphSearchService(
        repository=repository,
        searcher=ScriptedSearcher(matches=MATCHES, ranking=["deployment.md", "README.md"]),
        settings=get_settings(),
    )
    application = create_app()
    application.dependency_overrides[get_service] = lambda: service
    with TestClient(application) as client:
        yield client
    application.dependency_overrides.clear()


def _url(project_id: str) -> str:
    return SEARCH.format(project_id=project_id)


def test_search_returns_ranked_results(api: TestClient, seeded) -> None:
    project = seeded

    response = api.get(_url(project["id"]), params={"q": "deploy a release"})

    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "deploy a release"
    assert body["project_id"] == project["id"]
    assert [hit["name"] for hit in body["results"]] == ["deployment.md", "README.md"]
    assert body["results"][0]["path"] == "guides/deployment.md"
    assert body["opened_directories"] == ["", "guides"]
    assert body["traversal"]["model"] == "scripted"


def test_search_is_scoped_to_the_caller(
    api: TestClient, seeded, repository: InMemorySearchRepository
) -> None:
    project = seeded
    repository.projects[project["id"]]["owner_id"] = "someone-else"

    assert api.get(_url(project["id"]), params={"q": "deploy"}).status_code == 404


def test_a_short_query_is_rejected(api: TestClient, seeded) -> None:
    project = seeded

    response = api.get(_url(project["id"]), params={"q": "ab"})

    assert response.status_code == 400
    assert "at least" in response.json()["detail"]


def test_limit_bounds_are_rejected(api: TestClient, seeded) -> None:
    project = seeded

    assert api.get(_url(project["id"]), params={"q": "deploy", "limit": 0}).status_code == 400
    assert api.get(_url(project["id"]), params={"q": "deploy", "limit": 26}).status_code == 400


def test_the_optional_valve_is_accepted_and_reported(api: TestClient, seeded) -> None:
    project = seeded

    response = api.get(_url(project["id"]), params={"q": "deploy", "max_directories": 1})

    assert response.status_code == 200
    body = response.json()
    assert body["traversal"]["budget_exhausted"] is True
    assert body["opened_directories"] == [""]


def test_a_missing_query_is_a_validation_error(api: TestClient, seeded) -> None:
    project = seeded

    assert api.get(_url(project["id"])).status_code == 422
