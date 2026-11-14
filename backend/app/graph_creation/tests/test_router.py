"""HTTP contract of the Graph Creation routes (no background work, no network)."""

from __future__ import annotations

import asyncio
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.graph_creation.router import get_service
from app.graph_creation.service import GraphCreationService
from app.graph_creation.summarise import MockSummarizer
from app.graph_creation.tests.fakes import InMemoryGraphRepository, InMemoryObjectStore
from app.main import create_app


class _SyncService(GraphCreationService):
    """Service that records the scheduled job instead of running it."""

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)  # type: ignore[arg-type]
        self.scheduled = None

    def schedule(self, prepared):  # noqa: ANN001, ANN201 - test double
        self.scheduled = prepared


@pytest.fixture()
def repository() -> InMemoryGraphRepository:
    return InMemoryGraphRepository()


@pytest.fixture()
def service(repository: InMemoryGraphRepository) -> _SyncService:
    return _SyncService(
        repository=repository,
        store=InMemoryObjectStore(),
        summarizer=MockSummarizer(),
        settings=get_settings(),
    )


@pytest.fixture()
def api(service: _SyncService) -> Iterator[TestClient]:
    application = create_app()
    application.dependency_overrides[get_service] = lambda: service
    with TestClient(application) as client:
        yield client
    application.dependency_overrides.clear()


def test_upload_returns_accepted_with_a_job(api: TestClient, service: _SyncService) -> None:
    response = api.post(
        "/api/graph-creation/uploads",
        data={"mode": "new", "name": "Docs"},
        files=[
            ("files", ("docs/a.md", b"# A", "text/markdown")),
            ("files", ("README.md", b"# Root", "text/markdown")),
        ],
    )

    assert response.status_code == 202
    body = response.json()
    assert body["mode"] == "new"
    assert body["total_files"] == 2
    assert body["job_id"]
    assert service.scheduled is not None


def test_upload_rejects_a_broken_archive(api: TestClient) -> None:
    response = api.post(
        "/api/graph-creation/uploads",
        data={"mode": "new"},
        files=[("files", ("project.zip", b"not a zip", "application/zip"))],
    )

    assert response.status_code == 400
    assert "zip" in response.json()["detail"].lower()


def test_add_without_project_id_is_rejected(api: TestClient) -> None:
    response = api.post(
        "/api/graph-creation/uploads",
        data={"mode": "add"},
        files=[("files", ("a.md", b"# A", "text/markdown"))],
    )

    assert response.status_code == 400
    assert "project_id" in response.json()["detail"]


def test_projects_are_scoped_to_the_caller(
    api: TestClient, repository: InMemoryGraphRepository
) -> None:
    created = api.post(
        "/api/graph-creation/uploads",
        data={"mode": "new", "name": "Docs"},
        files=[("files", ("a.md", b"# A", "text/markdown"))],
    ).json()
    foreign = repository.projects[created["project_id"]]
    foreign["owner_id"] = "someone-else"
    repository.jobs[created["job_id"]]["owner_id"] = "someone-else"

    assert api.get("/api/graph-creation/projects").json() == []
    assert api.get(f"/api/graph-creation/projects/{created['project_id']}").status_code == 404
    assert api.get(f"/api/graph-creation/jobs/{created['job_id']}").status_code == 404


def test_tree_and_directory_responses_are_serialised(
    api: TestClient, service: _SyncService
) -> None:
    created = api.post(
        "/api/graph-creation/uploads",
        data={"mode": "new", "name": "Docs"},
        files=[
            ("files", ("docs/api/auth.md", b"# Auth\n\nHow auth works.", "text/markdown")),
            ("files", ("README.md", b"# Root", "text/markdown")),
        ],
    ).json()
    prepared = service.scheduled
    assert prepared is not None
    asyncio.run(service.run_job(prepared))

    tree = api.get(f"/api/graph-creation/projects/{created['project_id']}/tree").json()
    assert tree["project"]["name"] == "Docs"
    assert tree["tree"]["path"] == ""
    assert [child["path"] for child in tree["tree"]["directories"]] == ["docs"]
    assert tree["tree"]["directories"][0]["directories"][0]["files"][0]["name"] == "auth.md"

    doc_id = tree["tree"]["directories"][0]["id"]
    directory = api.get(f"/api/graph-creation/directories/{doc_id}").json()
    assert directory["directory"]["path"] == "docs"
    assert [child["path"] for child in directory["directories"]] == ["docs/api"]

    job = api.get(f"/api/graph-creation/jobs/{created['job_id']}").json()
    assert job["status"] == "ok"
    assert job["processed_files"] == 2
