"""Calendar: the merged personal view, project calendars, and event ownership."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
from fastapi import HTTPException

from app.calendar.schemas import EventIn, EventPatch
from app.calendar.service import CalendarService
from app.core.mentions import marker

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


# ------------------------------------------------------------------------- mentions


async def test_event_notes_store_the_mentions_they_carry(service: CalendarService, world) -> None:
    notes = (
        f"read {marker('file', world.document['id'], 'auth.md')} before "
        f"{marker('ticket', world.ticket_target['id'], 'Fix the login redirect')}"
    )

    created = await service.create_event(
        member_id=world.ada["id"],
        payload=EventIn(
            project_id=world.pulse["id"],
            title="Design review",
            notes=notes,
            starts_at=datetime(2026, 3, 18, 14, 0, tzinfo=UTC),
        ),
    )

    assert created["notes"] == notes
    assert [item["kind"] for item in created["mentions"]] == ["file", "ticket"]
    assert created["mentions"][0]["path"] == "pulse/guides/auth.md"
    assert created["mentions"][0]["directory_path"] == "pulse/guides"
    assert created["mentions"][1]["ticket_number"] == 12

    calendar = await service.project(
        member_id=world.ada["id"],
        project_id=world.pulse["id"],
        start=MARCH_START,
        end=MARCH_END,
    )
    item = next(row for row in calendar["items"] if row["title"] == "Design review")
    assert [entry["label"] for entry in item["mentions"]] == [
        "auth.md",
        "Fix the login redirect",
    ]


async def test_a_mention_from_another_project_is_refused(service: CalendarService, world) -> None:
    other = world.repository.seed_project("Other", world.ada["id"])
    foreign = world.catalogue.seed_target(other["id"], kind="file", label="secret.md")

    with pytest.raises(HTTPException) as error:
        await service.create_event(
            member_id=world.ada["id"],
            payload=EventIn(
                project_id=world.pulse["id"],
                title="Sneaky",
                notes=f"see {marker('file', foreign['id'], 'secret.md')}",
                starts_at=datetime(2026, 3, 18, 14, 0, tzinfo=UTC),
            ),
        )

    assert error.value.status_code == 400
    assert f"file:{foreign['id']}" in str(error.value.detail)


async def test_a_personal_event_keeps_markers_as_plain_notes(
    service: CalendarService, world
) -> None:
    notes = f"my own {marker('file', world.document['id'], 'auth.md')}"

    created = await service.create_event(
        member_id=world.ada["id"],
        payload=EventIn(
            title="Dentist",
            notes=notes,
            starts_at=datetime(2026, 3, 18, 14, 0, tzinfo=UTC),
        ),
    )

    assert created["project_id"] is None
    assert created["notes"] == notes
    assert created["mentions"] == []


async def test_editing_notes_rebuilds_the_resolved_mentions(
    service: CalendarService, world
) -> None:
    first = await service.create_event(
        member_id=world.ada["id"],
        payload=EventIn(
            project_id=world.pulse["id"],
            title="Review",
            notes=f"read {marker('file', world.document['id'], 'auth.md')}",
            starts_at=datetime(2026, 3, 18, 14, 0, tzinfo=UTC),
        ),
    )
    assert len(first["mentions"]) == 1

    cleared = await service.update_event(
        member_id=world.ada["id"], event_id=first["id"], payload=EventPatch(notes="no links now")
    )
    assert cleared["mentions"] == []

    refreshed = await service.update_event(
        member_id=world.ada["id"],
        event_id=first["id"],
        payload=EventPatch(
            notes=f"now the {marker('ticket', world.ticket_target['id'], 'Fix the login redirect')}"
        ),
    )
    assert [item["kind"] for item in refreshed["mentions"]] == ["ticket"]


async def test_mention_targets_are_scoped_to_the_project(service: CalendarService, world) -> None:
    other = world.repository.seed_project("Other", world.ada["id"])
    world.catalogue.seed_target(other["id"], kind="file", label="elsewhere.md")

    rows = await service.mention_targets(
        member_id=world.ada["id"], project_id=world.pulse["id"], query=""
    )

    assert {row["label"] for row in rows} == {"auth.md", "Fix the login redirect"}
    assert world.catalogue.searches == [(world.pulse["id"], "")]


async def test_mention_targets_need_membership(service: CalendarService, world) -> None:
    private = world.repository.seed_project("Private", world.ada["id"])

    with pytest.raises(HTTPException) as error:
        await service.mention_targets(
            member_id=world.bo["id"], project_id=private["id"], query="auth"
        )

    assert error.value.status_code == 404


async def test_events_mentioning_a_ticket_are_returned(service: CalendarService, world) -> None:
    ticket = marker("ticket", world.ticket_target["id"], "Fix the login redirect")
    created = await service.create_event(
        member_id=world.ada["id"],
        payload=EventIn(
            project_id=world.pulse["id"],
            title="Triage",
            notes=f"blocked by {ticket}",
            starts_at=datetime(2026, 3, 20, 9, 0, tzinfo=UTC),
        ),
    )

    rows = await service.events_mentioning(
        member_id=world.ada["id"],
        project_id=world.pulse["id"],
        kind="ticket",
        target_id=world.ticket_target["id"],
    )

    assert [row["id"] for row in rows] == [created["id"]]
    assert rows[0]["day"] == date(2026, 3, 20)
    assert rows[0]["project_name"] == "Pulse workspace"


async def test_events_mentioning_refuses_an_unknown_kind(service: CalendarService, world) -> None:
    with pytest.raises(HTTPException) as error:
        await service.events_mentioning(
            member_id=world.ada["id"],
            project_id=world.pulse["id"],
            kind="event",
            target_id=world.kickoff["id"],
        )

    assert error.value.status_code == 400
