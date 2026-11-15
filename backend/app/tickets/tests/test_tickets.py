"""Tickets: creation, the two list views, assignment and completion."""

from __future__ import annotations

from datetime import date

import pytest
from fastapi import HTTPException

from app.core.activity import (
    TICKET_ASSIGNED,
    TICKET_COMMENTED,
    TICKET_COMPLETED,
    TICKET_CREATED,
    TICKET_STATUS_CHANGED,
    TICKET_UPDATED,
)
from app.tickets.schemas import TicketCreateIn, TicketStatus, TicketUpdateIn
from app.tickets.service import TicketService
from app.tickets.tests.fakes import RecordingActivity


async def _ticket(service: TicketService, world, **fields):
    payload = TicketCreateIn(project_id=world.project["id"], **fields)
    return await service.create_ticket(member_id=world.ada["id"], payload=payload)


async def test_creation_defaults_the_assignee_to_the_caller(service: TicketService, world) -> None:
    ticket = await _ticket(service, world, title="Rotate the signing key")

    assert ticket["status"] == "todo"
    assert ticket["priority"] == "medium"
    assert ticket["assignee"]["id"] == world.ada["id"]
    assert ticket["project_name"] == "Pulse workspace"


async def test_ticket_numbers_are_per_project(service: TicketService, world) -> None:
    first = await _ticket(service, world, title="One")
    second = await _ticket(service, world, title="Two")

    assert (first["number"], second["number"]) == (1, 2)


async def test_a_ticket_can_be_given_to_another_member(service: TicketService, world) -> None:
    await service.share_project(world.project["id"], world.ada["id"], world.bo["id"])

    ticket = await _ticket(service, world, title="Review the runbook", assignee_id=world.bo["id"])

    assert ticket["assignee"]["display_name"] == "Bo Chen"


async def test_assigning_someone_outside_the_project_is_rejected(
    service: TicketService, world
) -> None:
    with pytest.raises(HTTPException) as error:
        await _ticket(service, world, title="Review", assignee_id=world.bo["id"])

    assert error.value.status_code == 400


async def test_labels_are_trimmed_deduplicated_and_capped(service: TicketService, world) -> None:
    ticket = await _ticket(service, world, title="Docs", labels=[" auth ", "Auth", "urgent"])

    assert ticket["labels"] == ["auth", "urgent"]


async def test_a_label_that_is_too_long_is_rejected(service: TicketService, world) -> None:
    with pytest.raises(HTTPException) as error:
        await _ticket(service, world, title="Docs", labels=["x" * 40])

    assert error.value.status_code == 400


async def test_due_date_and_priority_round_trip(service: TicketService, world) -> None:
    ticket = await _ticket(service, world, title="Ship", priority="high", due_date=date(2026, 3, 1))

    assert ticket["priority"] == "high"
    assert ticket["due_date"] == date(2026, 3, 1)


async def test_mine_lists_only_the_tickets_assigned_to_me(service: TicketService, world) -> None:
    await service.share_project(world.project["id"], world.ada["id"], world.bo["id"])
    mine = await _ticket(service, world, title="Mine")
    theirs = await _ticket(service, world, title="Theirs", assignee_id=world.bo["id"])

    listed = await service.list_tickets(member_id=world.ada["id"], scope="mine")

    assert [ticket["id"] for ticket in listed] == [mine["id"]]
    assert theirs["id"] not in {ticket["id"] for ticket in listed}


async def test_project_scope_lists_everyone_on_one_project(service: TicketService, world) -> None:
    await service.share_project(world.project["id"], world.ada["id"], world.bo["id"])
    await _ticket(service, world, title="Mine")
    await _ticket(service, world, title="Theirs", assignee_id=world.bo["id"])

    listed = await service.list_tickets(
        member_id=world.ada["id"], scope="project", project_id=world.project["id"]
    )

    assert len(listed) == 2


async def test_a_project_scope_needs_a_project(service: TicketService, world) -> None:
    with pytest.raises(HTTPException) as error:
        await service.list_tickets(member_id=world.ada["id"], scope="project")

    assert error.value.status_code == 400


async def test_open_tickets_sort_before_completed_ones(service: TicketService, world) -> None:
    done = await _ticket(service, world, title="Finished")
    await service.set_status(
        member_id=world.ada["id"], ticket_id=done["id"], new_status=TicketStatus.DONE
    )
    await _ticket(service, world, title="Still open")

    listed = await service.list_tickets(member_id=world.ada["id"])

    assert listed[-1]["status"] == "done"


async def test_completing_stamps_who_did_it_and_logs_the_event(
    service: TicketService, world, activity: RecordingActivity
) -> None:
    ticket = await _ticket(service, world, title="Fix the login redirect")

    completed = await service.set_status(
        member_id=world.ada["id"], ticket_id=ticket["id"], new_status=TicketStatus.DONE
    )

    assert completed["status"] == "done"
    assert completed["completed_by"]["id"] == world.ada["id"]
    assert completed["completed_at"] is not None
    assert TICKET_COMPLETED in activity.kinds()


async def test_reopening_clears_the_completion(service: TicketService, world) -> None:
    ticket = await _ticket(service, world, title="Fix the login redirect")
    await service.set_status(
        member_id=world.ada["id"], ticket_id=ticket["id"], new_status=TicketStatus.DONE
    )

    reopened = await service.set_status(
        member_id=world.ada["id"], ticket_id=ticket["id"], new_status=TicketStatus.TODO
    )

    assert reopened["completed_at"] is None
    assert reopened["completed_by"] is None


async def test_moving_to_in_progress_is_its_own_event(
    service: TicketService, world, activity: RecordingActivity
) -> None:
    ticket = await _ticket(service, world, title="Investigate latency")

    await service.set_status(
        member_id=world.ada["id"], ticket_id=ticket["id"], new_status=TicketStatus.IN_PROGRESS
    )

    assert activity.kinds()[-1] == TICKET_STATUS_CHANGED


async def test_editing_a_ticket_logs_the_changed_fields(
    service: TicketService, world, activity: RecordingActivity
) -> None:
    ticket = await _ticket(service, world, title="Fix the login redirect")

    updated = await service.update_ticket(
        member_id=world.ada["id"],
        ticket_id=ticket["id"],
        payload=TicketUpdateIn(description="Tokens rotate hourly.", priority="high"),
    )

    assert updated["description"] == "Tokens rotate hourly."
    assert updated["priority"] == "high"
    assert activity.kinds()[-1] == TICKET_UPDATED
    assert set(activity.events[-1]["detail"]["fields"]) == {"description", "priority"}


async def test_reassigning_logs_an_assignment_event(
    service: TicketService, world, activity: RecordingActivity
) -> None:
    await service.share_project(world.project["id"], world.ada["id"], world.bo["id"])
    ticket = await _ticket(service, world, title="Review")

    updated = await service.update_ticket(
        member_id=world.ada["id"],
        ticket_id=ticket["id"],
        payload=TicketUpdateIn(assignee_id=world.bo["id"]),
    )

    assert updated["assignee"]["display_name"] == "Bo Chen"
    assert TICKET_ASSIGNED in activity.kinds()


async def test_a_null_assignee_clears_it(service: TicketService, world) -> None:
    ticket = await _ticket(service, world, title="Unassigned soon")

    updated = await service.update_ticket(
        member_id=world.ada["id"],
        ticket_id=ticket["id"],
        payload=TicketUpdateIn(assignee_id=None),
    )

    assert updated["assignee"] is None


async def test_an_empty_title_is_rejected_on_update(service: TicketService, world) -> None:
    ticket = await _ticket(service, world, title="Has a title")

    with pytest.raises(HTTPException) as error:
        await service.update_ticket(
            member_id=world.ada["id"],
            ticket_id=ticket["id"],
            payload=TicketUpdateIn(title="   "),
        )

    assert error.value.status_code == 400


async def test_a_comment_is_stored_with_its_author(
    service: TicketService, world, activity: RecordingActivity
) -> None:
    ticket = await _ticket(service, world, title="Fix the login redirect")

    comment = await service.add_comment(
        member_id=world.ada["id"], ticket_id=ticket["id"], body="Reproduced on staging."
    )

    detail = await service.get_ticket(member_id=world.ada["id"], ticket_id=ticket["id"])
    assert comment["author"]["display_name"] == "Ada Lovelace"
    assert detail["comments"][0]["body"] == "Reproduced on staging."
    assert detail["comment_count"] == 1
    assert TICKET_COMMENTED in activity.kinds()


async def test_the_activity_feed_names_the_actor_and_the_ticket(
    service: TicketService, world
) -> None:
    ticket = await _ticket(service, world, title="Fix the login redirect")

    feed = await service.activity(member_id=world.ada["id"])

    assert feed[0]["kind"] == TICKET_CREATED
    assert feed[0]["actor"]["display_name"] == "Ada Lovelace"
    assert feed[0]["ticket_number"] == ticket["number"]


async def test_the_feed_only_covers_projects_the_member_can_see(
    service: TicketService, world
) -> None:
    await _ticket(service, world, title="Ada's ticket")

    feed = await service.activity(member_id=world.bo["id"])

    assert feed == []
