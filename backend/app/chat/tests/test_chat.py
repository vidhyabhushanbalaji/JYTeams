"""Chat: posting, the poll cursor, channels, mentions and deletion."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.chat.mentions import marker
from app.chat.service import DELETED_BODY, ChatService


async def _post(service: ChatService, world, body: str) -> dict:
    return await service.post_message(
        member_id=world.ada["id"], project_id=world.project["id"], body=body
    )


async def test_a_message_is_stored_with_its_resolved_mentions(service: ChatService, world) -> None:
    body = (
        f"check {marker('file', world.auth['id'], 'auth.md')} in "
        f"{marker('directory', world.guides['id'], 'guides')} "
        f"because of {marker('ticket', world.ticket['id'], 'Fix the login redirect')}"
    )

    message = await _post(service, world, body)

    assert message["body"] == body
    assert message["author"]["display_name"] == "Ada Lovelace"
    assert [item["kind"] for item in message["mentions"]] == ["file", "directory", "ticket"]
    auth = message["mentions"][0]
    assert (auth["path"], auth["directory_path"]) == ("pulse/guides/auth.md", "pulse/guides")
    assert message["mentions"][2]["ticket_number"] == 12
    assert message["deleted"] is False


async def test_an_event_mention_carries_the_day_it_sits_on(service: ChatService, world) -> None:
    body = f"notes from {marker('event', world.event['id'], 'Kickoff')}"

    message = await _post(service, world, body)

    assert [item["kind"] for item in message["mentions"]] == ["event"]
    assert message["mentions"][0]["event_day"] == "2026-03-03"
    assert message["mentions"][0]["label"] == "Kickoff"


async def test_an_event_from_another_project_is_refused(service: ChatService, world) -> None:
    other = world.repository.seed_project("Other", world.ada["id"])
    foreign = world.catalogue.seed_target(other["id"], kind="event", label="Elsewhere")

    with pytest.raises(HTTPException) as error:
        await _post(service, world, f"see {marker('event', foreign['id'], 'Elsewhere')}")

    assert error.value.status_code == 400


async def test_a_duplicate_mention_is_stored_once(service: ChatService, world) -> None:
    same = marker("file", world.auth["id"], "auth.md")

    message = await _post(service, world, f"look {same} and again {same}")

    assert len(message["mentions"]) == 1
    assert message["body"].count(same) == 2


async def test_a_mention_from_another_project_is_refused(service: ChatService, world) -> None:
    other = world.repository.seed_project("Other", world.ada["id"])
    world.catalogue.seed_target(other["id"], kind="file", label="secret.md")

    with pytest.raises(HTTPException) as error:
        await _post(service, world, f"see {marker('file', 'file-99', 'secret.md')}")

    assert error.value.status_code == 400
    assert "file:file-99" in str(error.value.detail)


async def test_an_unknown_mention_is_refused(service: ChatService, world) -> None:
    with pytest.raises(HTTPException) as error:
        await _post(service, world, f"see {marker('ticket', 'no-such-ticket', 'gone')}")

    assert error.value.status_code == 400


async def test_a_blank_message_is_refused(service: ChatService, world) -> None:
    with pytest.raises(HTTPException) as error:
        await _post(service, world, "   \n  ")

    assert error.value.status_code == 400


async def test_a_message_without_mentions_is_fine(service: ChatService, world) -> None:
    message = await _post(service, world, "Standup at ten.")

    assert message["mentions"] == []
    assert message["body"] == "Standup at ten."


async def test_a_non_member_cannot_read_or_post(service: ChatService, world) -> None:
    with pytest.raises(HTTPException) as read_error:
        await service.messages(member_id=world.bo["id"], project_id=world.project["id"])

    with pytest.raises(HTTPException) as post_error:
        await service.post_message(
            member_id=world.bo["id"], project_id=world.project["id"], body="hello"
        )

    assert (read_error.value.status_code, post_error.value.status_code) == (404, 404)


async def test_after_seq_returns_only_what_is_new(service: ChatService, world) -> None:
    first = await _post(service, world, "one")
    second = await _post(service, world, "two")

    newer = await service.messages(
        member_id=world.ada["id"], project_id=world.project["id"], after_seq=first["seq"]
    )

    assert [row["id"] for row in newer] == [second["id"]]


async def test_the_newest_page_is_chronological(service: ChatService, world) -> None:
    for index in range(4):
        await _post(service, world, f"message {index}")

    rows = await service.messages(
        member_id=world.ada["id"], project_id=world.project["id"], limit=2
    )

    assert [row["body"] for row in rows] == ["message 2", "message 3"]


async def test_channels_list_my_projects_by_activity(service: ChatService, world) -> None:
    quiet = world.repository.seed_project("Quiet", world.ada["id"])
    await _post(service, world, "hello")

    channels = await service.channels(world.ada["id"])

    assert [row["project_id"] for row in channels] == [world.project["id"], quiet["id"]]
    assert channels[0]["project_name"] == "Pulse workspace"
    assert channels[0]["last_message"]["body"] == "hello"
    assert channels[1]["last_message"] is None


async def test_the_author_can_delete_their_message(service: ChatService, world) -> None:
    message = await _post(service, world, f"look {marker('file', world.auth['id'], 'auth.md')}")

    await service.delete_message(member_id=world.ada["id"], message_id=message["id"])

    [stored] = await service.messages(member_id=world.ada["id"], project_id=world.project["id"])
    assert stored["body"] == DELETED_BODY
    assert stored["deleted"] is True
    assert stored["mentions"] == []


async def test_a_member_cannot_delete_someone_elses_message(service: ChatService, world) -> None:
    world.repository.share(world.project["id"], world.bo["id"])
    message = await _post(service, world, "ada's message")

    with pytest.raises(HTTPException) as error:
        await service.delete_message(member_id=world.bo["id"], message_id=message["id"])

    assert error.value.status_code == 403


async def test_the_project_owner_may_delete_any_message(service: ChatService, world) -> None:
    world.repository.share(world.project["id"], world.bo["id"])
    message = await service.post_message(
        member_id=world.bo["id"], project_id=world.project["id"], body="bo's message"
    )

    await service.delete_message(member_id=world.ada["id"], message_id=message["id"])

    [stored] = await service.messages(member_id=world.ada["id"], project_id=world.project["id"])
    assert stored["body"] == DELETED_BODY


async def test_mention_targets_are_scoped_to_the_project(service: ChatService, world) -> None:
    other = world.repository.seed_project("Other", world.ada["id"])
    world.catalogue.seed_target(other["id"], kind="file", label="elsewhere.md")

    rows = await service.mention_targets(
        member_id=world.ada["id"], project_id=world.project["id"], query=""
    )

    assert {row["label"] for row in rows} == {
        "auth.md",
        "guides",
        "Fix the login redirect",
        "Kickoff",
    }
    assert world.catalogue.searches == [(world.project["id"], "")]


async def test_mention_targets_need_membership(service: ChatService, world) -> None:
    with pytest.raises(HTTPException) as error:
        await service.mention_targets(
            member_id=world.bo["id"], project_id=world.project["id"], query="auth"
        )

    assert error.value.status_code == 404
