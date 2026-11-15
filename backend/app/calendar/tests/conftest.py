"""Fixtures for the calendar: an in-memory world, no Supabase, no network."""

from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import pytest

from app.calendar.service import CalendarService
from app.calendar.tests.fakes import (
    FakeDeadlines,
    FakeProjectAccess,
    InMemoryCalendarRepository,
    at,
)


@pytest.fixture()
def repository() -> InMemoryCalendarRepository:
    return InMemoryCalendarRepository()


@pytest.fixture()
def deadlines(repository: InMemoryCalendarRepository) -> FakeDeadlines:
    return FakeDeadlines(repository)


@pytest.fixture()
def service(repository: InMemoryCalendarRepository, deadlines: FakeDeadlines) -> CalendarService:
    return CalendarService(
        repository=repository, access=FakeProjectAccess(repository), deadlines=deadlines
    )


@pytest.fixture()
def world(repository: InMemoryCalendarRepository, deadlines: FakeDeadlines) -> SimpleNamespace:
    """Ada owns *Pulse* and *Orbit*; Bo is on both. Deadlines fall in March 2026."""
    ada = repository.seed_member("Ada Lovelace")
    bo = repository.seed_member("Bo Chen")
    pulse = repository.seed_project("Pulse workspace", ada["id"])
    orbit = repository.seed_project("Orbit", ada["id"])
    repository.share(pulse["id"], bo["id"])
    repository.share(orbit["id"], bo["id"])

    kickoff = repository.seed_event(
        member_id=ada["id"],
        project_id=pulse["id"],
        title="Kickoff",
        starts_at=at(date(2026, 3, 3), hour=10),
    )
    retro = repository.seed_event(
        member_id=bo["id"],
        project_id=pulse["id"],
        title="Retro",
        starts_at=at(date(2026, 3, 4), hour=15),
    )
    offsite = repository.seed_event(
        member_id=ada["id"],
        project_id=orbit["id"],
        title="Orbit offsite",
        starts_at=at(date(2026, 3, 5), hour=9),
    )
    personal = repository.seed_event(
        member_id=ada["id"],
        title="Dentist",
        starts_at=at(date(2026, 3, 6), hour=8),
        all_day=True,
    )
    bos_private = repository.seed_event(
        member_id=bo["id"],
        title="Bo's day off",
        starts_at=at(date(2026, 3, 7), hour=8),
        all_day=True,
    )

    deadlines.seed(
        project_id=pulse["id"],
        ticket_id="ticket-1",
        title="Fix the login redirect",
        due_date=date(2026, 3, 10),
        assignee_id=ada["id"],
        number=12,
    )
    deadlines.seed(
        project_id=pulse["id"],
        ticket_id="ticket-2",
        title="Rotate the signing key",
        due_date=date(2026, 3, 11),
        assignee_id=bo["id"],
        number=13,
    )
    deadlines.seed(
        project_id=orbit["id"],
        ticket_id="ticket-3",
        title="Write the release notes",
        due_date=date(2026, 3, 12),
        assignee_id=ada["id"],
        number=4,
    )

    return SimpleNamespace(
        repository=repository,
        deadlines=deadlines,
        ada=ada,
        bo=bo,
        pulse=pulse,
        orbit=orbit,
        kickoff=kickoff,
        retro=retro,
        offsite=offsite,
        personal=personal,
        bos_private=bos_private,
    )
