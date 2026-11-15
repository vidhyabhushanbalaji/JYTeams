"""Seed a hackathon demo: named members, a shared project, tickets, a comment and a feed.

Writes to the configured Supabase project through the normal service layer (service role), so
every row looks exactly like the app's own. **No model is called**: tickets, sharing and the file
lookup are local; only a placement would describe a folder, and this tool places nothing.

Run from ``backend/``::

    ..\\.venv\\Scripts\\python.exe -m app.tickets.tools.seed_demo --project-id <uuid>

Omit ``--project-id`` to use the newest project. If the project already has tickets the tool
stops instead of duplicating them (pass ``--force`` to add another set).
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import date, timedelta

from app.core.access import SupabaseProjectAccess
from app.core.activity import SupabaseActivityLog
from app.core.config import get_settings
from app.db.supabase import admin_client
from app.tickets.adapters import GraphSearchAdapter
from app.tickets.distill import build_distiller
from app.tickets.repository import SupabaseTicketRepository
from app.tickets.schemas import Priority, TicketCreateIn, TicketStatus, TicketUpdateIn
from app.tickets.service import TicketService

DEFAULT_NAMES = ("Ada Lovelace", "Bo Chen", "Cy Jones")

TICKETS = (
    {
        "title": "Fix the login redirect loop",
        "description": (
            "The OAuth callback bounces between /login and /callback when the session cookie "
            "is missing. Check the auth middleware and the token endpoint."
        ),
        "priority": Priority.HIGH,
        "due_in": 3,
        "labels": ["auth", "bug"],
    },
    {
        "title": "Write the release runbook",
        "description": (
            "Step-by-step deploy and rollback for the API: what to check, how to revert a "
            "release, who signs off."
        ),
        "priority": Priority.MEDIUM,
        "due_in": 7,
        "labels": ["docs", "release"],
    },
    {
        "title": "Rotate the signing key",
        "description": (
            "Quarterly rotation. Old tokens must keep verifying for 24 hours, so the previous "
            "key stays in the key set until then."
        ),
        "priority": Priority.MEDIUM,
        "due_in": None,
        "labels": ["auth", "ops"],
    },
    {
        "title": "Document the incident process",
        "description": "Who to page, what to write down, and where the timeline lives.",
        "priority": Priority.LOW,
        "due_in": None,
        "labels": ["docs"],
    },
)


def _newest_project() -> dict | None:
    response = (
        admin_client()
        .table("projects")
        .select("id, name, owner_id")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    rows = response.data or []
    return dict(rows[0]) if rows else None


def _project(project_id: str | None) -> dict:
    if project_id is None:
        project = _newest_project()
        if project is None:
            raise SystemExit("No project exists yet. Upload one first, or pass --project-id.")
        return project
    response = admin_client().table("projects").select("*").eq("id", project_id).limit(1).execute()
    rows = response.data or []
    if not rows:
        raise SystemExit(f"No project with id {project_id}.")
    return dict(rows[0])


async def seed(project: dict, names: tuple[str, ...], force: bool) -> None:
    settings = get_settings()
    repository = SupabaseTicketRepository()
    service = TicketService(
        repository=repository,
        access=SupabaseProjectAccess(),
        activity=SupabaseActivityLog(),
        search=GraphSearchAdapter(settings),
        distiller=build_distiller(settings),
        settings=settings,
    )

    existing = await repository.list_tickets(project_ids=[project["id"]], limit=1)
    if existing and not force:
        print(
            f"{project['name']!r} already has tickets; nothing changed. "
            "Pass --force to add another set."
        )
        return

    owner_id = str(project["owner_id"])
    members = [await service.sign_in(name) for name in names]
    for member in members:
        if str(member["id"]) != owner_id:
            await service.share_project(project["id"], owner_id, str(member["id"]))

    reporter = members[0]
    created = []
    for index, spec in enumerate(TICKETS):
        assignee = members[index % len(members)]
        due = date.today() + timedelta(days=spec["due_in"]) if spec["due_in"] else None
        ticket = await service.create_ticket(
            member_id=str(reporter["id"]),
            payload=TicketCreateIn(
                project_id=project["id"],
                title=spec["title"],
                description=spec["description"],
                assignee_id=str(assignee["id"]),
                priority=spec["priority"],
                due_date=due,
                labels=list(spec["labels"]),
            ),
        )
        created.append(ticket)
        print(f"  {index + 1}. #{ticket['number']} {ticket['title']} -> {assignee['display_name']}")

    # One completed ticket, so the feed and the "done" state are visible in the demo.
    finished = created[1]
    await service.set_status(
        member_id=str(reporter["id"]),
        ticket_id=str(finished["id"]),
        new_status=TicketStatus.DONE,
    )
    await service.update_ticket(
        member_id=str(reporter["id"]),
        ticket_id=str(created[0]["id"]),
        payload=TicketUpdateIn(
            description=(
                f"{TICKETS[0]['description']}\n\nReproduced on staging: the cookie is dropped "
                "when the redirect is cross-site."
            )
        ),
    )
    await service.add_comment(
        member_id=str(members[1]["id"]),
        ticket_id=str(created[0]["id"]),
        body="I can reproduce it - the callback loses the cookie on a cross-site redirect.",
    )

    files = await repository.list_files(str(project["id"]))
    for file in sorted(files, key=lambda row: str(row.get("name", "")))[:2]:
        await service.attach_file(
            member_id=str(reporter["id"]),
            ticket_id=str(created[0]["id"]),
            file_id=str(file["id"]),
        )

    print()
    print(f"Seeded {len(created)} tickets on {project['name']!r}.")
    print("Sign in as any of: " + ", ".join(names))
    print("Each name sees only the tickets assigned to it; the project is shared between them.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-id", help="Project to seed (default: the newest one)")
    parser.add_argument(
        "--names",
        default=", ".join(DEFAULT_NAMES),
        help="Comma separated names to create or find (the first one reports the tickets)",
    )
    parser.add_argument("--force", action="store_true", help="Add a set even if tickets exist")
    args = parser.parse_args()

    names = tuple(name.strip() for name in args.names.split(",") if name.strip())
    if not names:
        raise SystemExit("Give at least one name.")

    asyncio.run(seed(_project(args.project_id), names, args.force))


if __name__ == "__main__":
    main()
