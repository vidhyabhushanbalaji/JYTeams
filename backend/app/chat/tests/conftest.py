"""Fixtures for the chat section: an in-memory world, no Supabase, no network."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.chat.service import ChatService
from app.chat.tests.fakes import (
    FakeMentionCatalogue,
    FakeProjectAccess,
    InMemoryChatRepository,
)


@pytest.fixture()
def repository() -> InMemoryChatRepository:
    return InMemoryChatRepository()


@pytest.fixture()
def catalogue() -> FakeMentionCatalogue:
    return FakeMentionCatalogue()


@pytest.fixture()
def service(repository: InMemoryChatRepository, catalogue: FakeMentionCatalogue) -> ChatService:
    return ChatService(
        repository=repository, access=FakeProjectAccess(repository), catalogue=catalogue
    )


@pytest.fixture()
def world(repository: InMemoryChatRepository, catalogue: FakeMentionCatalogue) -> SimpleNamespace:
    """Ada owns *Pulse* (a folder and a document); Bo has not been shared with it yet."""
    ada = repository.seed_member("Ada Lovelace")
    bo = repository.seed_member("Bo Chen")
    project = repository.seed_project("Pulse workspace", ada["id"])
    guides = catalogue.seed_target(
        project["id"], kind="directory", label="guides", path="pulse/guides"
    )
    auth = catalogue.seed_target(
        project["id"],
        kind="file",
        label="auth.md",
        path="pulse/guides/auth.md",
        directory_path="pulse/guides",
    )
    ticket = catalogue.seed_target(
        project["id"], kind="ticket", label="Fix the login redirect", ticket_number=12
    )
    return SimpleNamespace(
        repository=repository,
        catalogue=catalogue,
        ada=ada,
        bo=bo,
        project=project,
        guides=guides,
        auth=auth,
        ticket=ticket,
    )
