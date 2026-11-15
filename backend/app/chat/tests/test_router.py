"""HTTP contract of the chat routes (in-memory repository, no Supabase, no network)."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.chat.mentions import marker
from app.chat.router import get_service
from app.chat.service import ChatService
from app.main import create_app

CHAT = "/api/chat"


@pytest.fixture()
def api(service: ChatService, world) -> Iterator[TestClient]:
    app = create_app()
    app.dependency_overrides[get_service] = lambda: service
    client = TestClient(app)
    client.headers.update({"X-Dev-User-Id": world.ada["id"]})
    yield client
    app.dependency_overrides.clear()


def _post(api: TestClient, world, body: str) -> dict:
    response = api.post(f"{CHAT}/projects/{world.project['id']}/messages", json={"body": body})
    assert response.status_code == 201, response.text
    return response.json()


def test_posting_and_reading_a_message(api: TestClient, world) -> None:
    body = f"check {marker('file', world.auth['id'], 'auth.md')} before the release"
    posted = _post(api, world, body)

    listed = api.get(f"{CHAT}/projects/{world.project['id']}/messages")

    assert posted["seq"] == 1
    assert posted["mentions"][0]["label"] == "auth.md"
    assert listed.status_code == 200
    assert [row["body"] for row in listed.json()] == [body]


def test_the_poll_cursor_only_returns_newer_messages(api: TestClient, world) -> None:
    first = _post(api, world, "one")
    second = _post(api, world, "two")

    response = api.get(
        f"{CHAT}/projects/{world.project['id']}/messages", params={"after_seq": first["seq"]}
    )

    assert [row["id"] for row in response.json()] == [second["id"]]


def test_an_empty_message_is_rejected_by_the_schema(api: TestClient, world) -> None:
    response = api.post(f"{CHAT}/projects/{world.project['id']}/messages", json={"body": ""})

    assert response.status_code == 422


def test_a_stranger_gets_404_from_the_chat(api: TestClient, world) -> None:
    api.headers["X-Dev-User-Id"] = world.bo["id"]

    assert api.get(f"{CHAT}/channels").json() == []
    assert api.get(f"{CHAT}/projects/{world.project['id']}/messages").status_code == 404
    assert (
        api.post(
            f"{CHAT}/projects/{world.project['id']}/messages", json={"body": "hello"}
        ).status_code
        == 404
    )


def test_the_author_deletes_a_message(api: TestClient, world) -> None:
    message = _post(api, world, "temporary")

    deleted = api.delete(f"{CHAT}/messages/{message['id']}")

    assert deleted.status_code == 204
    [stored] = api.get(f"{CHAT}/projects/{world.project['id']}/messages").json()
    assert stored["deleted"] is True


def test_channels_carry_the_last_message(api: TestClient, world) -> None:
    _post(api, world, "standup at ten")

    channels = api.get(f"{CHAT}/channels").json()

    assert [row["project_name"] for row in channels] == ["Pulse workspace"]
    assert channels[0]["last_message"]["body"] == "standup at ten"


def test_mention_targets_answer_for_the_composer(api: TestClient, world) -> None:
    response = api.get(
        f"{CHAT}/projects/{world.project['id']}/mention-targets", params={"q": "auth"}
    )

    assert response.status_code == 200
    assert [row["label"] for row in response.json()] == ["auth.md"]
