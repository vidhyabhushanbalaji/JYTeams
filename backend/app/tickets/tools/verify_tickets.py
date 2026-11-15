"""Offline walkthrough of the tickets section: no Supabase, no network, no model calls.

Seeds an in-memory project, signs two people in, shares it, creates a ticket and opens it twice
(so the cached search is visible: two opens, one search), attaches a document, completes the task
and prints the activity feed. The distiller is the offline one, so the walkthrough shows the same
reduction the app makes without a key.
"""

from __future__ import annotations

import asyncio

from app.core.config import get_settings
from app.tickets.schemas import TicketCreateIn, TicketStatus
from app.tickets.service import TicketService
from app.tickets.tests.fakes import (
    FakeDistiller,
    FakeProjectAccess,
    FakeTicketSearch,
    InMemoryTicketRepository,
    RecordingActivity,
)


def _hit(file: dict) -> dict:
    return {
        "file_id": file["id"],
        "name": file["name"],
        "path": file["path"],
        "directory_id": file["directory_id"],
        "directory_path": "pulse/guides",
        "score": 0.81,
        "matched_terms": ["login", "redirect"],
        "excerpt": "The callback checks the session cookie before issuing a token.",
    }


async def main() -> None:
    repository = InMemoryTicketRepository()
    activity = RecordingActivity(repository)
    search = FakeTicketSearch()
    service = TicketService(
        repository=repository,
        access=FakeProjectAccess(repository),
        activity=activity,
        search=search,
        distiller=FakeDistiller(),
        settings=get_settings(),
    )

    ada = repository.seed_member("Ada Lovelace")
    bo = repository.seed_member("Bo Chen")
    project = repository.seed_project("Pulse workspace", ada["id"])
    guides = repository.seed_directory(project["id"], "guides", "pulse/guides")
    auth = repository.seed_file(
        project["id"],
        directory_id=guides["id"],
        name="auth.md",
        path="pulse/guides/auth.md",
        size_bytes=2048,
    )
    search.hits = [_hit(auth)]

    await service.share_project(project["id"], ada["id"], bo["id"])
    print("Members:", [member["display_name"] for member in await service.list_members()])
    shared = await service.list_project_members(project["id"], bo["id"])
    print("Shared with:", [member["display_name"] for member in shared])

    ticket = await service.create_ticket(
        member_id=ada["id"],
        payload=TicketCreateIn(
            project_id=project["id"],
            title="Fix the login redirect",
            description="The OAuth callback bounces between /login and /callback.",
            assignee_id=bo["id"],
        ),
    )
    print(f"Created #{ticket['number']} {ticket['title']} for {ticket['assignee']['display_name']}")

    first = await service.get_ticket(member_id=bo["id"], ticket_id=ticket["id"])
    await service.get_ticket(member_id=bo["id"], ticket_id=ticket["id"])
    print("Suggested files:", [item["name"] for item in first["files"]["suggested"]])
    print(f"Searches run for two opens: {len(search.calls)} (the second read used the cache)")

    await service.attach_file(member_id=bo["id"], ticket_id=ticket["id"], file_id=auth["id"])
    await service.set_status(
        member_id=bo["id"], ticket_id=ticket["id"], new_status=TicketStatus.DONE
    )
    detail = await service.get_ticket(member_id=bo["id"], ticket_id=ticket["id"])
    attached = [item["name"] for item in detail["files"]["attached"]]
    print("Status:", detail["status"], "| attached:", attached)

    print("Activity feed:")
    for event in await service.activity(member_id=ada["id"]):
        print(f"  - {event['kind']} by {event['actor']['display_name']}")

    assert len(search.calls) == 1, "the second open should have reused the cache"
    print()
    print("OK: identity, sharing, the cached search, attachment and completion all behaved.")


if __name__ == "__main__":
    asyncio.run(main())
