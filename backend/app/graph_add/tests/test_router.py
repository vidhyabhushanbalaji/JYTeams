"""HTTP contract of the Graph Add routes (in-memory repository, no network)."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.graph_add.router import get_service
from app.graph_add.service import GraphAddService
from app.graph_add.tests.fakes import (
    InMemoryAddRepository,
    InMemoryObjectStore,
    ScriptedNavigator,
)
from app.main import create_app

DOC = b"# Auth\n\nToken refresh and session expiry."
SUGGEST = "/api/graph-add/suggestions"
PLACE = "/api/graph-add/placements"


@pytest.fixture()
def repository() -> InMemoryAddRepository:
    return InMemoryAddRepository()


@pytest.fixture()
def seeded(repository: InMemoryAddRepository):
    project = repository.seed_project()
    docs = repository.seed_directory(
        project["id"],
        parent_id=project["root_directory_id"],
        name="docs",
        description="Guides and how-tos.",
    )
    return project, docs


@pytest.fixture()
def api(repository: InMemoryAddRepository) -> Iterator[TestClient]:
    service = GraphAddService(
        repository=repository,
        store=InMemoryObjectStore(),
        navigator=ScriptedNavigator(matches={"": [("docs", 0.9)]}),
        settings=get_settings(),
    )
    application = create_app()
    application.dependency_overrides[get_service] = lambda: service
    with TestClient(application) as client:
        yield client
    application.dependency_overrides.clear()


def _upload(api: TestClient, project_id: str, *, filename: str = "auth.md", data: bytes = DOC):
    return api.post(
        SUGGEST,
        data={"project_id": project_id},
        files={"file": (filename, data, "text/markdown")},
    )


def test_suggestion_endpoint_returns_ranked_locations(api: TestClient, seeded) -> None:
    project, _ = seeded

    response = _upload(api, project["id"])

    assert response.status_code == 200
    body = response.json()
    assert body["request_id"]
    assert body["file"]["name"] == "auth.md"
    assert body["suggestions"][0]["path"] == "docs"
    assert body["suggestions"][-1]["path"] == ""
    assert body["traversal"]["model"] == "scripted"


def test_suggestion_rejects_a_non_markdown_upload(api: TestClient, seeded) -> None:
    project, _ = seeded

    response = _upload(api, project["id"], filename="diagram.png", data=b"\x89PNG")

    assert response.status_code == 415


def test_suggestion_rejects_an_empty_upload(api: TestClient, seeded) -> None:
    project, _ = seeded

    response = _upload(api, project["id"], data=b"")

    assert response.status_code == 400


def test_suggestion_is_scoped_to_the_caller(
    api: TestClient, seeded, repository: InMemoryAddRepository
) -> None:
    project, _ = seeded
    repository.projects[project["id"]]["owner_id"] = "someone-else"

    assert _upload(api, project["id"]).status_code == 404


def test_placement_endpoint_creates_the_file(api: TestClient, seeded) -> None:
    project, docs = seeded
    suggestion = _upload(api, project["id"]).json()

    response = api.post(
        PLACE,
        json={
            "request_id": suggestion["request_id"],
            "directory_id": suggestion["suggestions"][0]["directory_id"],
            "placement": "direct",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["file"]["path"] == "docs/auth.md"
    assert body["directory_path"] == "docs"
    assert body["created_directory"] is False
    assert docs["name"] == "docs"


def test_placement_can_create_a_new_directory(api: TestClient, seeded) -> None:
    project, _ = seeded
    suggestion = _upload(api, project["id"]).json()

    response = api.post(
        PLACE,
        json={
            "request_id": suggestion["request_id"],
            "directory_id": suggestion["suggestions"][0]["directory_id"],
            "placement": "new_directory",
            "new_directory_name": "authentication",
        },
    )

    assert response.status_code == 201
    assert response.json()["file"]["path"] == "docs/authentication/auth.md"


def test_placement_conflict_returns_alternatives(api: TestClient, seeded) -> None:
    project, _ = seeded
    suggestion = _upload(api, project["id"]).json()
    payload = {
        "request_id": suggestion["request_id"],
        "directory_id": suggestion["suggestions"][0]["directory_id"],
    }

    assert api.post(PLACE, json=payload).status_code == 201
    conflict = api.post(PLACE, json=payload)

    assert conflict.status_code == 409
    assert "already been used" in conflict.json()["detail"]["message"]


def test_suggestion_can_be_read_back(api: TestClient, seeded) -> None:
    project, _ = seeded
    suggestion = _upload(api, project["id"]).json()

    replay = api.get(f"{SUGGEST}/{suggestion['request_id']}")

    assert replay.status_code == 200
    assert replay.json()["suggestions"] == suggestion["suggestions"]


def test_unknown_suggestion_is_a_404(api: TestClient, seeded) -> None:
    assert api.get(f"{SUGGEST}/nope").status_code == 404
