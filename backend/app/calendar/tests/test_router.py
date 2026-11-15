"""HTTP contract of the calendar routes (in-memory repository, no Supabase, no network)."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.calendar.router import get_service
from app.calendar.service import CalendarService
from app.main import create_app

CALENDAR = "/api/calendar"
RANGE = {"from": "2026-03-01", "to": "2026-03-31"}


@pytest.fixture()
def api(service: CalendarService, world) -> Iterator[TestClient]:
    app = create_app()
    app.dependency_overrides[get_service] = lambda: service
    client = TestClient(app)
    client.headers.update({"X-Dev-User-Id": world.ada["id"]})
    yield client
    app.dependency_overrides.clear()


def test_the_personal_calendar_answers_a_range(api: TestClient, world) -> None:
    response = api.get(f"{CALENDAR}/personal", params=RANGE)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["scope"] == "personal"
    assert body["start"] == "2026-03-01"
    assert {"Kickoff", "Fix the login redirect"} <= {item["title"] for item in body["items"]}


def test_the_personal_calendar_needs_a_range(api: TestClient) -> None:
    assert api.get(f"{CALENDAR}/personal").status_code == 422


def test_a_project_calendar_answers(api: TestClient, world) -> None:
    response = api.get(f"{CALENDAR}/projects/{world.pulse['id']}", params=RANGE)

    assert response.status_code == 200, response.text
    assert response.json()["project_name"] == "Pulse workspace"


def test_a_stranger_gets_404_from_a_project_calendar(api: TestClient, world) -> None:
    api.headers["X-Dev-User-Id"] = world.bo["id"]
    private = world.repository.seed_project("Private", world.ada["id"])

    assert api.get(f"{CALENDAR}/projects/{private['id']}", params=RANGE).status_code == 404


def test_adding_an_event(api: TestClient, world) -> None:
    response = api.post(
        f"{CALENDAR}/events",
        json={
            "project_id": world.pulse["id"],
            "title": "Design review",
            "starts_at": "2026-03-18T14:00:00+00:00",
            "notes": "bring the wireframes",
        },
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["title"] == "Design review"
    assert body["project_name"] == "Pulse workspace"
    assert body["created_by"]["display_name"] == "Ada Lovelace"


def test_an_event_that_ends_before_it_starts_is_rejected(api: TestClient) -> None:
    response = api.post(
        f"{CALENDAR}/events",
        json={
            "title": "Impossible",
            "starts_at": "2026-03-18T14:00:00+00:00",
            "ends_at": "2026-03-18T13:00:00+00:00",
        },
    )

    assert response.status_code == 422


def test_editing_and_deleting_an_event(api: TestClient, world) -> None:
    event_id = world.kickoff["id"]

    patched = api.patch(f"{CALENDAR}/events/{event_id}", json={"title": "Kickoff (moved)"})
    deleted = api.delete(f"{CALENDAR}/events/{event_id}")

    assert patched.status_code == 200
    assert patched.json()["title"] == "Kickoff (moved)"
    assert deleted.status_code == 204


def test_a_non_creator_cannot_edit_an_event(api: TestClient, world) -> None:
    api.headers["X-Dev-User-Id"] = world.bo["id"]

    response = api.patch(
        f"{CALENDAR}/events/{world.kickoff['id']}", json={"title": "Renamed by Bo"}
    )

    assert response.status_code == 403
