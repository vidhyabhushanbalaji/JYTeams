"""HTTP contract of the tickets routes (in-memory repository, no Supabase, no network)."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.tickets.router import get_service
from app.tickets.service import TicketService
from app.tickets.tests.fakes import InMemoryTicketRepository

TICKETS = "/api/tickets"


@pytest.fixture()
def api(service: TicketService, world) -> Iterator[TestClient]:
    app = create_app()
    app.dependency_overrides[get_service] = lambda: service
    client = TestClient(app)
    client.headers.update({"X-Dev-User-Id": world.ada["id"]})
    yield client
    app.dependency_overrides.clear()


def _create(api: TestClient, world, **overrides) -> dict:
    payload = {"project_id": world.project["id"], "title": "Rotate the signing key"}
    payload.update(overrides)
    response = api.post(f"{TICKETS}/tickets", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_the_name_list_needs_no_identity(api: TestClient, world) -> None:
    api.headers.pop("X-Dev-User-Id")

    response = api.get(f"{TICKETS}/members")

    assert response.status_code == 200
    assert [row["display_name"] for row in response.json()] == [
        "Ada Lovelace",
        "Bo Chen",
        "Cy Jones",
    ]


def test_signing_in_returns_the_member(api: TestClient) -> None:
    response = api.post(f"{TICKETS}/members", json={"display_name": "Grace Hopper"})

    assert response.status_code == 200
    assert response.json()["display_name"] == "Grace Hopper"


def test_me_answers_404_for_an_unknown_identity(api: TestClient, world) -> None:
    api.headers["X-Dev-User-Id"] = "not-a-member"

    response = api.get(f"{TICKETS}/me")

    assert response.status_code == 404


def test_a_member_can_read_themselves(api: TestClient, world) -> None:
    response = api.get(f"{TICKETS}/me")

    assert response.status_code == 200
    assert response.json()["id"] == world.ada["id"]


def test_creating_a_ticket(api: TestClient, world) -> None:
    body = _create(api, world)

    assert body["number"] == 1
    assert body["status"] == "todo"
    assert body["assignee"]["display_name"] == "Ada Lovelace"
    assert body["project_name"] == "Pulse workspace"


def test_the_default_list_is_my_todos(api: TestClient, world) -> None:
    _create(api, world)

    response = api.get(f"{TICKETS}/tickets")

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_a_project_list_carries_every_ticket(api: TestClient, world) -> None:
    _create(api, world)

    response = api.get(
        f"{TICKETS}/tickets", params={"scope": "project", "project_id": world.project["id"]}
    )

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_an_unknown_ticket_is_404(api: TestClient) -> None:
    response = api.get(f"{TICKETS}/tickets/does-not-exist")

    assert response.status_code == 404


def test_detail_carries_comments_and_files(api: TestClient, world, search) -> None:
    ticket = _create(api, world, title="Fix the login redirect")

    response = api.get(f"{TICKETS}/tickets/{ticket['id']}")

    assert response.status_code == 200
    body = response.json()
    assert body["comments"] == []
    assert set(body["files"]) >= {"query", "suggested", "attached", "cached_at", "stale"}
    assert len(search.calls) == 1


def test_completing_a_ticket_over_http(api: TestClient, world) -> None:
    ticket = _create(api, world)

    response = api.post(f"{TICKETS}/tickets/{ticket['id']}/status", json={"status": "done"})

    assert response.status_code == 200
    assert response.json()["status"] == "done"


def test_a_comment_over_http(api: TestClient, world) -> None:
    ticket = _create(api, world)

    response = api.post(
        f"{TICKETS}/tickets/{ticket['id']}/comments", json={"body": "Reproduced on staging."}
    )

    assert response.status_code == 201
    assert response.json()["author"]["display_name"] == "Ada Lovelace"


def test_attaching_and_detaching_a_document(api: TestClient, world) -> None:
    ticket = _create(api, world)

    attached = api.post(
        f"{TICKETS}/tickets/{ticket['id']}/files", json={"file_id": world.auth["id"]}
    )
    assert attached.status_code == 200
    assert attached.json()["attached"][0]["file_id"] == world.auth["id"]

    removed = api.delete(f"{TICKETS}/tickets/{ticket['id']}/files/{world.auth['id']}")
    assert removed.status_code == 204


def test_attaching_without_a_file_id_is_a_validation_error(api: TestClient, world) -> None:
    ticket = _create(api, world)

    response = api.post(f"{TICKETS}/tickets/{ticket['id']}/files", json={})

    assert response.status_code == 422


def test_the_activity_feed_over_http(api: TestClient, world) -> None:
    _create(api, world)

    response = api.get(f"{TICKETS}/activity", params={"project_id": world.project["id"]})

    assert response.status_code == 200
    feed = response.json()
    assert feed[0]["kind"] == "ticket_created"
    assert feed[0]["actor"]["display_name"] == "Ada Lovelace"


def test_sharing_over_http(api: TestClient, world) -> None:
    response = api.post(
        f"{TICKETS}/projects/{world.project['id']}/members", json={"member_id": world.bo["id"]}
    )

    assert response.status_code == 200
    assert response.json()["display_name"] == "Bo Chen"


def test_a_stranger_cannot_read_a_projects_members(
    api: TestClient, world, repository: InMemoryTicketRepository
) -> None:
    api.headers["X-Dev-User-Id"] = world.bo["id"]

    response = api.get(f"{TICKETS}/projects/{world.project['id']}/members")

    assert response.status_code == 404
