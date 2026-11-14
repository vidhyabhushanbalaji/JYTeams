"""HTTP contract of the search route (in-memory repository and storage, no network)."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.graph_ai_search.router import get_service
from app.graph_ai_search.scoring import LocalScorer
from app.graph_ai_search.service import GraphSearchService
from app.graph_ai_search.storage import BlobCache, DocumentTextReader
from app.graph_ai_search.tests.fakes import FakeBlobStore, InMemorySearchRepository
from app.main import create_app

SEARCH = "/api/graph-ai-search/projects/{project_id}/search"


@pytest.fixture()
def repository() -> InMemorySearchRepository:
    return InMemorySearchRepository()


@pytest.fixture()
def seeded(repository: InMemorySearchRepository):
    project = repository.seed_project(owner_id="user-1")
    root = project["root_directory_id"]
    repository.seed_file(
        project["id"],
        directory_id=root,
        name="README.md",
        body="# PulseAPI\n\nEvent ingestion overview.",
    )
    guides = repository.seed_directory(
        project["id"],
        parent_id=root,
        name="guides",
        description="Deployment and release procedures.",
    )
    repository.seed_file(
        project["id"],
        directory_id=guides["id"],
        name="deployment.md",
        body="# Deployment\n\nRoll back a release with the previous chart.",
    )
    return project


@pytest.fixture()
def api(repository: InMemorySearchRepository, seeded) -> Iterator[TestClient]:
    service = GraphSearchService(
        repository=repository,
        reader=DocumentTextReader(
            store=FakeBlobStore.from_repository(repository), cache=BlobCache(max_entries=4)
        ),
        scorer=LocalScorer(),
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

    response = api.get(_url(project["id"]), params={"q": "deployment release"})

    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "deployment release"
    assert body["project_id"] == project["id"]
    assert [hit["name"] for hit in body["results"]] == ["deployment.md"]
    assert body["results"][0]["path"] == "guides/deployment.md"
    assert "deployment" in body["results"][0]["matched_terms"]
    assert body["results"][0]["excerpt"]
    assert "guides" in body["opened_directories"]
    assert body["traversal"]["scorer_version"] == LocalScorer().version
    assert body["traversal"]["files_read"] >= 1


def test_optional_context_is_accepted(api: TestClient, seeded) -> None:
    project = seeded

    response = api.get(
        _url(project["id"]), params={"q": "zzz qqq", "context": "deployment release"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["context"] == "deployment release"
    assert [hit["name"] for hit in body["results"]] == ["deployment.md"]


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
