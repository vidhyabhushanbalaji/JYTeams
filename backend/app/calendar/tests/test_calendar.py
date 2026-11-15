"""Calendar: the merged personal view, project calendars, and event ownership."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
from fastapi import HTTPException

from app.calendar.schemas import EventIn, EventPatch
from app.calendar.service import CalendarService

MARCH_START = date(2026, 3, 1)
MARCH_END = date(2026, 3, 31)


def _titles(items: list[dict]) -> list[str]:
    return [item["title"] for item in items]


async def test_the_personal_calendar_merges_my_projects(service: CalendarService, world) -> None:
    calendar = await service.personal(member_id=world.ada["id"], start=MARCH_START, end=MARCH_END)

    assert calendar["scope"] == "personal"
    assert calendar["project_name"] == "My calendar"
    assert set(_titles(calendar["items"])) == {
        "Kickoff",
        "Retro",
        "Orbit offsite",
        "Dentist",
        "Fix the login redirect",
        "Write the release notes",
    }
    assert "Bo's day off" not in _titles(calendar["items"])


async def test_the_personal_calendar_only_shows_my_deadlines(
    service: CalendarService, world
) -> None:
    calendar = await service.personal(member_id=world.ada["id"], start=MARCH_START, end=MARCH_END)

    numbers = [item["ticket_number"] for item in calendar["items"] if item["kind"] == "deadline"]
    assert numbers == [12, 4]
    assert world.deadlines.calls[-1]["assignee_id"] == world.ada["id"]


async def test_a_project_calendar_carries_every_deadline(service: CalendarService, world) -> None:
    calendar = await service.project(
        member_id=world.ada["id"],
        project_id=world.pulse["id"],
        start=MARCH_START,
        end=MARCH_END,
    )

    assert calendar["scope"] == "project"
    assert calendar["project_name"] == "Pulse workspace"
    assert set(_titles(calendar["items"])) == {
        "Kickoff",
        "Retro",
        "Fix the login redirect",
        "Rotate the signing key",
    }
    assert world.deadlines.calls[-1] == {
        "project_ids": [world.pulse["id"]],
        "assignee_id": None,
        "start": MARCH_START,
        "end": MARCH_END,
    }


async def test_items_are_ordered_by_day_with_events_first(service: CalendarService, world) -> None:
    calendar = await service.project(
        member_id=world.ada["id"],
        project_id=world.pulse["id"],
        start=MARCH_START,
        end=MARCH_END,
    )

    days = [item["day"] for item in calendar["items"]]
    assert days == sorted(days)
    assert _titles(calendar["items"]) == [
        "Kickoff",
        "Retro",
        "Fix the login redirect",
        "Rotate the signing key",
    ]


async def test_a_deadline_carries_its_ticket_and_assignee(service: CalendarService, world) -> None:
    calendar = await service.project(
        member_id=world.ada["id"],
        project_id=world.pulse["id"],
        start=MARCH_START,
        end=MARCH_END,
    )
    deadline = next(item for item in calendar["items"] if item["kind"] == "deadline")

    assert deadline["ticket_id"] == "ticket-1"
    assert deadline["ticket_number"] == 12
    assert deadline["status"] == "todo"
    assert deadline["assignee"]["display_name"] == "Ada Lovelace"
    assert deadline["all_day"] is True
    assert deadline["editable"] is False


async def test_only_what_i_added_is_editable(service: CalendarService, world) -> None:
    calendar = await service.personal(member_id=world.ada["id"], start=MARCH_START, end=MARCH_END)

    editable = {item["title"]: item["editable"] for item in calendar["items"]}
    assert editable["Kickoff"] is True
    assert editable["Retro"] is False


async def test_a_stranger_cannot_read_a_project_calendar(service: CalendarService, world) -> None:
    private = world.repository.seed_project("Private", world.ada["id"])

    with pytest.raises(HTTPException) as error:
        await service.project(
            member_id=world.bo["id"],
            project_id=private["id"],
            start=MARCH_START,
            end=MARCH_END,
        )

    assert error.value.status_code == 404


async def test_a_personal_event_is_added_without_a_project(service: CalendarService, world) -> None:
    event = await service.create_event(
        member_id=world.ada["id"],
        payload=EventIn(
            title="  Dentist  ",
            starts_at=datetime(2026, 3, 20, 9, 0, tzinfo=UTC),
            all_day=True,
        ),
    )

    assert event["title"] == "Dentist"
    assert event["project_id"] is None
    assert event["created_by"]["display_name"] == "Ada Lovelace"


async def test_a_project_event_needs_membership(service: CalendarService, world) -> None:
    private = world.repository.seed_project("Private", world.ada["id"])

    with pytest.raises(HTTPException) as error:
        await service.create_event(
            member_id=world.bo["id"],
            payload=EventIn(
                project_id=private["id"],
                title="Sneaky",
                starts_at=datetime(2026, 3, 20, 9, 0, tzinfo=UTC),
            ),
        )

    assert error.value.status_code == 404


async def test_a_title_of_only_spaces_is_refused(service: CalendarService, world) -> None:
    with pytest.raises(HTTPException) as error:
        await service.create_event(
            member_id=world.ada["id"],
            payload=EventIn(title="   ", starts_at=datetime(2026, 3, 20, 9, 0, tzinfo=UTC)),
        )

    assert error.value.status_code == 400


async def test_only_the_creator_may_edit_an_event(service: CalendarService, world) -> None:
    with pytest.raises(HTTPException) as error:
        await service.update_event(
            member_id=world.bo["id"],
            event_id=world.kickoff["id"],
            payload=EventPatch(title="Renamed by Bo"),
        )

    assert error.value.status_code == 403


async def test_the_creator_edits_their_event(service: CalendarService, world) -> None:
    updated = await service.update_event(
        member_id=world.ada["id"],
        event_id=world.kickoff["id"],
        payload=EventPatch(title="Kickoff (moved)", notes="bring the runbook"),
    )

    assert updated["title"] == "Kickoff (moved)"
    assert updated["notes"] == "bring the runbook"
    assert updated["project_name"] == "Pulse workspace"


async def test_an_edit_cannot_end_before_it_starts(service: CalendarService, world) -> None:
    with pytest.raises(HTTPException) as error:
        await service.update_event(
            member_id=world.ada["id"],
            event_id=world.kickoff["id"],
            payload=EventPatch(ends_at=datetime(2026, 3, 1, 9, 0, tzinfo=UTC)),
        )

    assert error.value.status_code == 400


async def test_the_creator_deletes_their_event(service: CalendarService, world) -> None:
    await service.delete_event(member_id=world.ada["id"], event_id=world.kickoff["id"])

    assert world.kickoff["id"] not in world.repository.events


async def test_deleting_an_unknown_event_is_a_404(service: CalendarService, world) -> None:
    with pytest.raises(HTTPException) as error:
        await service.delete_event(member_id=world.ada["id"], event_id="event-missing")

    assert error.value.status_code == 404


async def test_a_range_that_ends_before_it_starts_is_refused(
    service: CalendarService, world
) -> None:
    with pytest.raises(HTTPException) as error:
        await service.personal(member_id=world.ada["id"], start=MARCH_END, end=MARCH_START)

    assert error.value.status_code == 400


async def test_a_range_longer_than_the_cap_is_refused(service: CalendarService, world) -> None:
    with pytest.raises(HTTPException) as error:
        await service.personal(
            member_id=world.ada["id"], start=date(2024, 1, 1), end=date(2026, 1, 1)
        )

    assert error.value.status_code == 400
