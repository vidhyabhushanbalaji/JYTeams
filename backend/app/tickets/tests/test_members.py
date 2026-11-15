"""Identity (a name, no password) and project sharing."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.core.activity import PROJECT_MEMBER_REMOVED, PROJECT_SHARED, TICKET_CREATED
from app.tickets.schemas import TicketCreateIn
from app.tickets.service import TicketService
from app.tickets.tests.fakes import InMemoryTicketRepository, RecordingActivity


async def test_signing_in_with_a_new_name_creates_a_member(service: TicketService) -> None:
    member = await service.sign_in("Grace Hopper")

    assert member["display_name"] == "Grace Hopper"
    assert (await service.list_members())[0]["id"] == member["id"]


async def test_signing_in_again_finds_the_same_member(service: TicketService) -> None:
    first = await service.sign_in("Grace Hopper")
    second = await service.sign_in("  grace   hopper ")

    assert first["id"] == second["id"]


async def test_a_blank_name_is_rejected(service: TicketService) -> None:
    with pytest.raises(HTTPException) as error:
        await service.sign_in("   ")

    assert error.value.status_code == 400


async def test_me_rejects_an_identity_that_is_not_a_member(service: TicketService) -> None:
    with pytest.raises(HTTPException) as error:
        await service.current_member("not-a-member")

    assert error.value.status_code == 404


async def test_the_name_list_is_alphabetical(service: TicketService, world) -> None:
    names = [member["display_name"] for member in await service.list_members()]

    assert names == ["Ada Lovelace", "Bo Chen", "Cy Jones"]


async def test_the_owner_shares_a_project_and_the_activity_feed_says_so(
    service: TicketService, world, activity: RecordingActivity
) -> None:
    await service.share_project(world.project["id"], world.ada["id"], world.bo["id"])

    members = await service.list_project_members(world.project["id"], world.bo["id"])
    assert {member["display_name"] for member in members} == {"Ada Lovelace", "Bo Chen"}
    assert PROJECT_SHARED in activity.kinds()


async def test_a_shared_member_can_work_on_the_project(service: TicketService, world) -> None:
    await service.share_project(world.project["id"], world.ada["id"], world.bo["id"])

    ticket = await service.create_ticket(
        member_id=world.bo["id"],
        payload=TicketCreateIn(project_id=world.project["id"], title="Wire the token endpoint"),
    )

    assert ticket["reporter"]["display_name"] == "Bo Chen"


async def test_a_stranger_cannot_see_the_project(service: TicketService, world) -> None:
    with pytest.raises(HTTPException) as error:
        await service.list_project_members(world.project["id"], world.bo["id"])

    assert error.value.status_code == 404


async def test_only_the_owner_may_share(service: TicketService, world) -> None:
    await service.share_project(world.project["id"], world.ada["id"], world.bo["id"])

    with pytest.raises(HTTPException) as error:
        await service.share_project(world.project["id"], world.bo["id"], world.cy["id"])

    assert error.value.status_code == 403


async def test_sharing_twice_is_idempotent(
    service: TicketService, world, activity: RecordingActivity
) -> None:
    await service.share_project(world.project["id"], world.ada["id"], world.bo["id"])
    await service.share_project(world.project["id"], world.ada["id"], world.bo["id"])

    assert activity.kinds().count(PROJECT_SHARED) == 1


async def test_sharing_with_an_unknown_member_is_404(service: TicketService, world) -> None:
    with pytest.raises(HTTPException) as error:
        await service.share_project(world.project["id"], world.ada["id"], "nobody")

    assert error.value.status_code == 404


async def test_unsharing_removes_access(
    service: TicketService, world, activity: RecordingActivity
) -> None:
    await service.share_project(world.project["id"], world.ada["id"], world.bo["id"])

    await service.unshare_project(world.project["id"], world.ada["id"], world.bo["id"])

    assert PROJECT_MEMBER_REMOVED in activity.kinds()
    with pytest.raises(HTTPException):
        await service.list_project_members(world.project["id"], world.bo["id"])


async def test_the_owner_cannot_be_removed(service: TicketService, world) -> None:
    with pytest.raises(HTTPException) as error:
        await service.unshare_project(world.project["id"], world.ada["id"], world.ada["id"])

    assert error.value.status_code == 400


async def test_seeded_tickets_are_attributed_to_their_reporter(
    service: TicketService,
    world,
    repository: InMemoryTicketRepository,
    activity: RecordingActivity,
) -> None:
    ticket = await service.create_ticket(
        member_id=world.ada["id"],
        payload=TicketCreateIn(project_id=world.project["id"], title="Rotate the signing key"),
    )

    assert ticket["reporter"]["id"] == world.ada["id"]
    assert activity.kinds() == [TICKET_CREATED]
    assert repository.tickets[ticket["id"]]["reporter_id"] == world.ada["id"]
