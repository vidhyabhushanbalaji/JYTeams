"""Fixtures for the tickets section: an in-memory world, no Supabase, no network."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.core.config import get_settings
from app.tickets.service import TicketService
from app.tickets.tests.fakes import (
    FakeDistiller,
    FakeProjectAccess,
    FakeTicketSearch,
    InMemoryTicketRepository,
    RecordingActivity,
)


@pytest.fixture()
def repository() -> InMemoryTicketRepository:
    return InMemoryTicketRepository()


@pytest.fixture()
def search() -> FakeTicketSearch:
    return FakeTicketSearch()


@pytest.fixture()
def distiller() -> FakeDistiller:
    """The offline reduction, which is what the app uses when no model key is configured."""
    return FakeDistiller()


@pytest.fixture()
def activity(repository: InMemoryTicketRepository) -> RecordingActivity:
    return RecordingActivity(repository)


@pytest.fixture()
def service(
    repository: InMemoryTicketRepository,
    search: FakeTicketSearch,
    distiller: FakeDistiller,
    activity: RecordingActivity,
) -> TicketService:
    return TicketService(
        repository=repository,
        access=FakeProjectAccess(repository),
        activity=activity,
        search=search,
        distiller=distiller,
        settings=get_settings(),
    )


@pytest.fixture()
def world(repository: InMemoryTicketRepository) -> SimpleNamespace:
    """Ada owns *Pulse* (two folders, two documents); Bo has not been shared with it yet."""
    ada = repository.seed_member("Ada Lovelace")
    bo = repository.seed_member("Bo Chen")
    cy = repository.seed_member("Cy Jones")
    project = repository.seed_project("Pulse workspace", ada["id"])
    root = repository.seed_directory(project["id"], "pulse", "pulse")
    guides = repository.seed_directory(project["id"], "guides", "pulse/guides")
    auth = repository.seed_file(
        project["id"],
        directory_id=guides["id"],
        name="auth.md",
        path="pulse/guides/auth.md",
        size_bytes=2048,
    )
    deploy = repository.seed_file(
        project["id"],
        directory_id=root["id"],
        name="deploy.md",
        path="pulse/deploy.md",
        updated_at="2026-01-02T00:00:00+00:00",
    )
    return SimpleNamespace(
        repository=repository,
        ada=ada,
        bo=bo,
        cy=cy,
        project=project,
        root=root,
        guides=guides,
        auth=auth,
        deploy=deploy,
    )


def hit(file: dict, *, score: float = 0.8, directory_path: str = "pulse/guides") -> dict:
    """A Graph AI Search hit for one seeded file."""
    return {
        "file_id": file["id"],
        "name": file["name"],
        "path": file["path"],
        "directory_id": file["directory_id"],
        "directory_path": directory_path,
        "score": score,
        "matched_terms": ["auth"],
        "excerpt": "Tokens are issued here.",
    }
