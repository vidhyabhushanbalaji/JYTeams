"""HTTP contract of the Graph Add routes (in-memory repository and storage, no network)."""

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
    ScriptedDescriber,
)
from app.main import create_app

SUGGEST = "/api/graph-add/suggestions"
PLACE = "/api/graph-add/placements"
DOCUMENT = b"# Rollback runbook\n\nRoll back a failed release with the previous Helm chart.\n"


@pytest.fixture()
def repository() -> InMemoryAddRepository:
    return InMemoryAddRepository()


@pytest.fixture()
def seeded(repository: InMemoryAddRepository):
    project = repository.seed_project(owner_id="user-1")
    root_id = project["root_directory_id"]
    repository.directories[root_id]["description"] = "Release documentation."
    guides = repository.seed_directory(
        project["id"],
        parent_id=root_id,
        name="guides",
        description="Deployment and release procedures, including rollback steps.",
    )
    return project, guides


@pytest.fixture()
def api(repository: InMemoryAddRepository, seeded) -> Iterator[TestClient]:
    service = GraphAddService(
        repository=repository,
        store=InMemoryObjectStore(),
        describer=ScriptedDescriber(),
        settings=get_settings(),
    )
    application = create_app()
    application.dependency_overrides[get_service] = lambda: service
    with TestClient(application) as client:
        yield client
    application.dependency_overrides.clear()


def _suggest(api: TestClient, project_id: str):
    return api.post(
        SUGGEST,
        files={"file": ("rollback-runbook.md", DOCUMENT, "text/markdown")},
        data={"project_id": project_id},
    )


def test_suggest_returns_ranked_suggestions(api: TestClient, seeded) -> None:
    project, _ = seeded

    response = _suggest(api, project["id"])

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {
        "request_id",
        "project_id",
        "status",
        "expires_at",
        "context",
        "file",
        "suggestions",
        "scan",
    }
    assert body["file"]["preview"].startswith("# Rollback runbook")
    assert body["suggestions"][0]["path"] == "guides"
    assert "rollback" in body["suggestions"][0]["matched_terms"]
    assert body["scan"]["folders_scored"] == 2
    assert body["scan"]["scorer_version"]


def test_place_returns_the_created_file(api: TestClient, seeded) -> None:
    project, guides = seeded
    suggestion = _suggest(api, project["id"]).json()

    response = api.post(
        PLACE,
        json={
            "request_id": suggestion["request_id"],
            "directory_id": guides["id"],
            "placement": "direct",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["file"]["path"] == "guides/rollback-runbook.md"
    assert body["file"]["summary_status"] == "skipped"
    assert body["created_directory"] is False
    assert body["refreshed_directories"] == 2


def test_a_replayed_suggestion_matches_what_was_shown(api: TestClient, seeded) -> None:
    project, _ = seeded
    suggestion = _suggest(api, project["id"]).json()

    response = api.get(f"{SUGGEST}/{suggestion['request_id']}")

    assert response.status_code == 200
    assert response.json()["suggestions"] == suggestion["suggestions"]
    assert response.json()["file"]["preview"] == suggestion["file"]["preview"]


def test_a_non_markdown_upload_is_rejected(api: TestClient, seeded) -> None:
    project, _ = seeded

    response = api.post(
        SUGGEST,
        files={"file": ("diagram.png", b"\x89PNG\r\n", "image/png")},
        data={"project_id": project["id"]},
    )

    assert response.status_code == 415


def test_an_empty_upload_is_rejected(api: TestClient, seeded) -> None:
    project, _ = seeded

    response = api.post(
        SUGGEST,
        files={"file": ("empty.md", b"", "text/markdown")},
        data={"project_id": project["id"]},
    )

    assert response.status_code == 400


def test_a_missing_file_is_a_validation_error(api: TestClient, seeded) -> None:
    project, _ = seeded

    assert api.post(SUGGEST, data={"project_id": project["id"]}).status_code == 422


def test_another_users_suggestion_is_not_found(
    api: TestClient, seeded, repository: InMemoryAddRepository
) -> None:
    project, _ = seeded
    suggestion = _suggest(api, project["id"]).json()
    repository.requests[suggestion["request_id"]]["owner_id"] = "someone-else"

    assert api.get(f"{SUGGEST}/{suggestion['request_id']}").status_code == 404
