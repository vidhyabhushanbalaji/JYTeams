"""A ticket's documents: the cached search, attaching files, and staleness."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.core.activity import FILE_ATTACHED, FILE_DETACHED
from app.tickets.distill import SearchTerms
from app.tickets.schemas import TicketCreateIn, TicketUpdateIn
from app.tickets.service import TicketService
from app.tickets.tests.conftest import hit
from app.tickets.tests.fakes import (
    FakeDistiller,
    FakeTicketSearch,
    InMemoryTicketRepository,
    RecordingActivity,
)


async def _ticket(service: TicketService, world, **fields):
    payload = TicketCreateIn(project_id=world.project["id"], **fields)
    return await service.create_ticket(member_id=world.ada["id"], payload=payload)


async def test_the_first_open_searches_the_distilled_terms(
    service: TicketService,
    world,
    search: FakeTicketSearch,
    distiller: FakeDistiller,
) -> None:
    distiller.result = SearchTerms(
        query="decision rights accurate", points=("decision rights", "approval authority")
    )
    search.hits = [hit(world.auth)]
    ticket = await _ticket(
        service,
        world,
        title="Review whether decision rights are still accurate",
        description=(
            "Pasted from the customer call. Acceptance criteria: the governance team reviews the "
            "page before Friday, then the ticket is closed by the reporter."
        ),
    )

    detail = await service.get_ticket(member_id=world.ada["id"], ticket_id=ticket["id"])

    assert len(search.calls) == 1
    # The search sees the distilled terms, never the ticket's own long-winded text.
    assert search.calls[0]["query"] == "decision rights accurate"
    assert search.calls[0]["context"] == "decision rights · approval authority"
    assert search.calls[0]["limit"] == 5
    assert search.calls[0]["member_id"] == world.ada["id"]
    assert len(distiller.calls) == 1
    assert detail["files"]["query"] == "decision rights accurate"
    assert detail["files"]["context"] == "decision rights · approval authority"
    assert detail["files"]["suggested"][0]["file_id"] == world.auth["id"]
    assert detail["files"]["suggested"][0]["directory_path"] == "pulse/guides"
    assert detail["files"]["cached_at"] is not None
    assert detail["files"]["stale"] is False


async def test_without_a_scripted_model_the_ticket_still_reduces_its_own_words(
    service: TicketService,
    world,
    search: FakeTicketSearch,
    distiller: FakeDistiller,
) -> None:
    """With no model configured the offline reduction runs: process words are dropped."""
    search.hits = [hit(world.auth)]
    ticket = await _ticket(
        service,
        world,
        title="Review whether auth token rotation is still accurate",
    )

    await service.get_ticket(member_id=world.ada["id"], ticket_id=ticket["id"])

    query = search.calls[0]["query"]
    assert "auth" in query
    assert "whether" not in query
    assert "review" not in query
    assert len(distiller.calls) == 1


async def test_reopening_the_ticket_reuses_the_cache(
    service: TicketService, world, search: FakeTicketSearch, distiller: FakeDistiller
) -> None:
    search.hits = [hit(world.auth)]
    ticket = await _ticket(service, world, title="Fix auth token rotation")

    await service.get_ticket(member_id=world.ada["id"], ticket_id=ticket["id"])
    again = await service.get_ticket(member_id=world.ada["id"], ticket_id=ticket["id"])

    assert len(search.calls) == 1
    assert len(distiller.calls) == 1
    assert again["files"]["suggested"][0]["file_id"] == world.auth["id"]


async def test_the_files_endpoint_is_the_same_cache(
    service: TicketService, world, search: FakeTicketSearch
) -> None:
    search.hits = [hit(world.auth)]
    ticket = await _ticket(service, world, title="Fix auth token rotation")

    await service.ticket_files(member_id=world.ada["id"], ticket_id=ticket["id"])
    payload = await service.ticket_files(member_id=world.ada["id"], ticket_id=ticket["id"])

    assert len(search.calls) == 1
    assert payload["suggested"][0]["file_id"] == world.auth["id"]


async def test_editing_the_description_makes_the_cache_stale(
    service: TicketService, world, search: FakeTicketSearch, distiller: FakeDistiller
) -> None:
    search.hits = [hit(world.auth)]
    ticket = await _ticket(service, world, title="Fix auth token rotation")
    await service.get_ticket(member_id=world.ada["id"], ticket_id=ticket["id"])

    await service.update_ticket(
        member_id=world.ada["id"],
        ticket_id=ticket["id"],
        payload=TicketUpdateIn(description="Now also about refresh tokens."),
    )
    await service.get_ticket(member_id=world.ada["id"], ticket_id=ticket["id"])

    assert len(search.calls) == 2
    # New wording means the terms are distilled again, once.
    assert len(distiller.calls) == 2


async def test_a_new_project_document_makes_the_cache_stale(
    service: TicketService,
    world,
    search: FakeTicketSearch,
    distiller: FakeDistiller,
    repository: InMemoryTicketRepository,
) -> None:
    search.hits = [hit(world.auth)]
    ticket = await _ticket(service, world, title="Fix auth token rotation")
    await service.get_ticket(member_id=world.ada["id"], ticket_id=ticket["id"])

    repository.seed_file(
        world.project["id"],
        directory_id=world.guides["id"],
        name="refresh.md",
        updated_at="2026-02-01T00:00:00+00:00",
    )
    await service.get_ticket(member_id=world.ada["id"], ticket_id=ticket["id"])

    assert len(search.calls) == 2
    # The ticket's words did not change, so the model is not asked again: only the search re-runs.
    assert len(distiller.calls) == 1


async def test_refresh_forces_a_new_search(
    service: TicketService, world, search: FakeTicketSearch, distiller: FakeDistiller
) -> None:
    search.hits = [hit(world.auth)]
    ticket = await _ticket(service, world, title="Fix auth token rotation")
    await service.get_ticket(member_id=world.ada["id"], ticket_id=ticket["id"])

    await service.ticket_files(member_id=world.ada["id"], ticket_id=ticket["id"], refresh=True)

    assert len(search.calls) == 2
    assert len(distiller.calls) == 1


async def test_a_model_outage_falls_back_to_the_tickets_own_words(
    service: TicketService, world, search: FakeTicketSearch, distiller: FakeDistiller
) -> None:
    distiller.error = RuntimeError("503 unavailable")
    search.hits = [hit(world.auth)]
    ticket = await _ticket(
        service, world, title="Fix auth token rotation", description="Tokens rotate hourly."
    )

    detail = await service.get_ticket(member_id=world.ada["id"], ticket_id=ticket["id"])

    assert search.calls[0]["query"] == "Fix auth token rotation"
    assert search.calls[0]["context"] == "Tokens rotate hourly."
    assert detail["files"]["suggested"][0]["file_id"] == world.auth["id"]

    # A failure is not cached as if it were a distillation: the next open asks the model again,
    # and with the same fallback terms the search itself is still reused.
    await service.get_ticket(member_id=world.ada["id"], ticket_id=ticket["id"])
    assert len(distiller.calls) == 2
    assert len(search.calls) == 1


async def test_a_distilled_query_too_short_to_search_falls_back_to_the_title(
    service: TicketService, world, search: FakeTicketSearch, distiller: FakeDistiller
) -> None:
    distiller.result = SearchTerms(query="ab")
    search.hits = [hit(world.auth)]
    ticket = await _ticket(service, world, title="Fix auth token rotation")

    await service.get_ticket(member_id=world.ada["id"], ticket_id=ticket["id"])

    assert search.calls[0]["query"] == "Fix auth token rotation"


async def test_a_ticket_with_nothing_to_search_says_so(
    service: TicketService, world, search: FakeTicketSearch, distiller: FakeDistiller
) -> None:
    # The model found no words worth searching for: the ticket explains itself instead.
    distiller.result = SearchTerms(query="")
    ticket = await _ticket(service, world, title="UI", description="ok")

    payload = await service.ticket_files(member_id=world.ada["id"], ticket_id=ticket["id"])

    assert payload["suggested"] == []
    assert payload["reason"] is not None
    assert search.calls == []

    # "Nothing to search for" is a settled answer: reopening does not ask the model again.
    await service.ticket_files(member_id=world.ada["id"], ticket_id=ticket["id"])
    assert len(distiller.calls) == 1


async def test_a_hit_for_a_missing_document_is_dropped_and_flagged(
    service: TicketService, world, search: FakeTicketSearch
) -> None:
    ghost = hit(world.auth, score=0.4) | {"file_id": "file-gone", "name": "gone.md"}
    search.hits = [hit(world.auth), ghost]
    ticket = await _ticket(service, world, title="Fix auth token rotation")

    payload = await service.ticket_files(member_id=world.ada["id"], ticket_id=ticket["id"])

    assert [item["file_id"] for item in payload["suggested"]] == [world.auth["id"]]
    assert payload["stale"] is True


async def test_attaching_an_existing_file(
    service: TicketService, world, activity: RecordingActivity
) -> None:
    ticket = await _ticket(service, world, title="Fix auth token rotation")

    await service.attach_file(
        member_id=world.ada["id"], ticket_id=ticket["id"], file_id=world.auth["id"]
    )

    payload = await service.ticket_files(member_id=world.ada["id"], ticket_id=ticket["id"])
    assert payload["attached"][0]["file_id"] == world.auth["id"]
    assert payload["attached"][0]["directory_path"] == "pulse/guides"
    assert payload["attached"][0]["added_by"]["display_name"] == "Ada Lovelace"
    assert FILE_ATTACHED in activity.kinds()


async def test_attaching_does_not_complete_the_ticket(service: TicketService, world) -> None:
    ticket = await _ticket(service, world, title="Fix auth token rotation")

    await service.attach_file(
        member_id=world.ada["id"], ticket_id=ticket["id"], file_id=world.auth["id"]
    )

    detail = await service.get_ticket(member_id=world.ada["id"], ticket_id=ticket["id"])
    assert detail["status"] == "todo"
    assert detail["attachment_count"] == 1


async def test_attaching_the_same_file_twice_logs_once(
    service: TicketService, world, activity: RecordingActivity
) -> None:
    ticket = await _ticket(service, world, title="Fix auth token rotation")

    await service.attach_file(
        member_id=world.ada["id"], ticket_id=ticket["id"], file_id=world.auth["id"]
    )
    await service.attach_file(
        member_id=world.ada["id"], ticket_id=ticket["id"], file_id=world.auth["id"]
    )

    assert activity.kinds().count(FILE_ATTACHED) == 1


async def test_attaching_a_file_from_another_project_is_404(
    service: TicketService, world, repository: InMemoryTicketRepository
) -> None:
    other = repository.seed_project("Other", world.cy["id"])
    directory = repository.seed_directory(other["id"], "other", "other")
    foreign = repository.seed_file(
        other["id"], directory_id=directory["id"], name="secret.md", path="other/secret.md"
    )
    ticket = await _ticket(service, world, title="Fix auth token rotation")

    with pytest.raises(HTTPException) as error:
        await service.attach_file(
            member_id=world.ada["id"], ticket_id=ticket["id"], file_id=foreign["id"]
        )

    assert error.value.status_code == 404


async def test_detaching_removes_the_file_but_not_the_document(
    service: TicketService,
    world,
    activity: RecordingActivity,
    repository: InMemoryTicketRepository,
) -> None:
    ticket = await _ticket(service, world, title="Fix auth token rotation")
    await service.attach_file(
        member_id=world.ada["id"], ticket_id=ticket["id"], file_id=world.auth["id"]
    )

    await service.detach_file(
        member_id=world.ada["id"], ticket_id=ticket["id"], file_id=world.auth["id"]
    )

    payload = await service.ticket_files(member_id=world.ada["id"], ticket_id=ticket["id"])
    assert payload["attached"] == []
    assert world.auth["id"] in repository.files
    assert FILE_DETACHED in activity.kinds()


async def test_detaching_something_that_is_not_attached_is_404(
    service: TicketService, world
) -> None:
    ticket = await _ticket(service, world, title="Fix auth token rotation")

    with pytest.raises(HTTPException) as error:
        await service.detach_file(
            member_id=world.ada["id"], ticket_id=ticket["id"], file_id=world.auth["id"]
        )

    assert error.value.status_code == 404


async def test_a_project_without_a_tree_still_opens_the_ticket(
    service: TicketService, world, search: FakeTicketSearch
) -> None:
    async def refuse(**_: object) -> dict:
        raise HTTPException(status_code=409, detail="This project has no directory tree yet.")

    search.search = refuse  # type: ignore[method-assign]
    ticket = await _ticket(service, world, title="Fix auth token rotation")

    detail = await service.get_ticket(member_id=world.ada["id"], ticket_id=ticket["id"])

    assert detail["files"]["suggested"] == []
    assert detail["files"]["reason"] == "This project has no directory tree yet."


async def test_a_ticket_from_a_project_you_cannot_see_is_404(service: TicketService, world) -> None:
    ticket = await _ticket(service, world, title="Fix auth token rotation")

    with pytest.raises(HTTPException) as error:
        await service.get_ticket(member_id=world.bo["id"], ticket_id=ticket["id"])

    assert error.value.status_code == 404
