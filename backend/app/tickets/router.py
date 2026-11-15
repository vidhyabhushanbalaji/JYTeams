"""HTTP routes for the Tickets section.

Mounted at ``/api/tickets``. Identity is a name (no password): ``POST /members`` signs in,
``GET /me`` tells the app whether the stored identity still exists, and every other route works
inside the projects that member can see.

A ticket's files are read with the ticket: the first open distils the ticket's own words into a
short search query (one model call) and runs Graph AI Search, storing both on the ticket, so
reopening it is free and a project change only re-runs the (model-free) search.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from app.core.access import SupabaseProjectAccess
from app.core.activity import SupabaseActivityLog
from app.core.auth import CurrentUser, get_current_user
from app.core.config import get_settings
from app.tickets.adapters import GraphSearchAdapter
from app.tickets.distill import build_distiller
from app.tickets.repository import SupabaseTicketRepository
from app.tickets.schemas import (
    AttachIn,
    CommentIn,
    CommentOut,
    MemberOut,
    ProjectMemberOut,
    ShareIn,
    SignInIn,
    TicketCreateIn,
    TicketDetailOut,
    TicketEventOut,
    TicketFilesOut,
    TicketOut,
    TicketStatusIn,
    TicketUpdateIn,
)
from app.tickets.service import TicketService

router = APIRouter(tags=["Tickets"])


def get_service() -> TicketService:
    """Wire the service (Supabase repository, membership + activity, search and distiller)."""
    settings = get_settings()
    return TicketService(
        repository=SupabaseTicketRepository(),
        access=SupabaseProjectAccess(),
        activity=SupabaseActivityLog(),
        search=GraphSearchAdapter(settings),
        distiller=build_distiller(settings),
        settings=settings,
    )


ServiceDep = Annotated[TicketService, Depends(get_service)]
UserDep = Annotated[CurrentUser, Depends(get_current_user)]


@router.post("/members", response_model=MemberOut, summary="Sign in with a name")
async def sign_in(payload: SignInIn, service: ServiceDep) -> MemberOut:
    return MemberOut(**await service.sign_in(payload.display_name))


@router.get("/members", response_model=list[MemberOut], summary="Names to sign in with")
async def list_members(service: ServiceDep) -> list[MemberOut]:
    return [MemberOut(**row) for row in await service.list_members()]


@router.get("/me", response_model=MemberOut, summary="Who the caller is")
async def current_member(user: UserDep, service: ServiceDep) -> MemberOut:
    return MemberOut(**await service.current_member(user.id))


@router.get(
    "/projects/{project_id}/members",
    response_model=list[ProjectMemberOut],
    summary="Who can see a project",
)
async def list_project_members(
    project_id: str, user: UserDep, service: ServiceDep
) -> list[ProjectMemberOut]:
    rows = await service.list_project_members(project_id, user.id)
    return [ProjectMemberOut(**row) for row in rows]


@router.post(
    "/projects/{project_id}/members",
    response_model=MemberOut,
    summary="Share a project with a member (owner only)",
)
async def share_project(
    project_id: str, payload: ShareIn, user: UserDep, service: ServiceDep
) -> MemberOut:
    return MemberOut(**await service.share_project(project_id, user.id, payload.member_id))


@router.delete(
    "/projects/{project_id}/members/{member_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Stop sharing a project with a member (owner only)",
)
async def unshare_project(
    project_id: str, member_id: str, user: UserDep, service: ServiceDep
) -> Response:
    await service.unshare_project(project_id, user.id, member_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/tickets", response_model=list[TicketOut], summary="Tickets assigned to me or on a project"
)
async def list_tickets(
    user: UserDep,
    service: ServiceDep,
    scope: Annotated[str, Query(description="mine (default) or project")] = "mine",
    project_id: Annotated[str | None, Query(description="Restrict to one project")] = None,
    status_filter: Annotated[
        str | None, Query(alias="status", description="todo, in_progress or done")
    ] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 200,
) -> list[TicketOut]:
    rows = await service.list_tickets(
        member_id=user.id,
        scope=scope,
        project_id=project_id,
        status_filter=status_filter,
        limit=limit,
    )
    return [TicketOut(**row) for row in rows]


@router.post(
    "/tickets",
    status_code=status.HTTP_201_CREATED,
    response_model=TicketOut,
    summary="Create a ticket",
)
async def create_ticket(payload: TicketCreateIn, user: UserDep, service: ServiceDep) -> TicketOut:
    return TicketOut(**await service.create_ticket(member_id=user.id, payload=payload))


@router.get(
    "/tickets/{ticket_id}",
    response_model=TicketDetailOut,
    summary="One ticket with its comments and files",
)
async def get_ticket(
    ticket_id: str,
    user: UserDep,
    service: ServiceDep,
    refresh: Annotated[
        bool, Query(description="Recompute the ticket's file suggestions now")
    ] = False,
) -> TicketDetailOut:
    return TicketDetailOut(
        **await service.get_ticket(member_id=user.id, ticket_id=ticket_id, refresh=refresh)
    )


@router.patch(
    "/tickets/{ticket_id}",
    response_model=TicketOut,
    summary="Update a ticket (only the fields you send)",
)
async def update_ticket(
    ticket_id: str, payload: TicketUpdateIn, user: UserDep, service: ServiceDep
) -> TicketOut:
    return TicketOut(
        **await service.update_ticket(member_id=user.id, ticket_id=ticket_id, payload=payload)
    )


@router.post(
    "/tickets/{ticket_id}/status",
    response_model=TicketOut,
    summary="Move a ticket, or tick its completion box",
)
async def set_status(
    ticket_id: str, payload: TicketStatusIn, user: UserDep, service: ServiceDep
) -> TicketOut:
    return TicketOut(
        **await service.set_status(
            member_id=user.id, ticket_id=ticket_id, new_status=payload.status
        )
    )


@router.get(
    "/tickets/{ticket_id}/files",
    response_model=TicketFilesOut,
    summary="The documents this ticket is about (cached search)",
)
async def ticket_files(
    ticket_id: str,
    user: UserDep,
    service: ServiceDep,
    refresh: Annotated[bool, Query(description="Recompute now instead of using the cache")] = False,
) -> TicketFilesOut:
    return TicketFilesOut(
        **await service.ticket_files(member_id=user.id, ticket_id=ticket_id, refresh=refresh)
    )


@router.post(
    "/tickets/{ticket_id}/files",
    response_model=TicketFilesOut,
    summary="Attach a document that is already in the project",
)
async def attach_file(
    ticket_id: str, payload: AttachIn, user: UserDep, service: ServiceDep
) -> TicketFilesOut:
    await service.attach_file(
        member_id=user.id,
        ticket_id=ticket_id,
        file_id=payload.file_id,
        source=payload.source,
    )
    return TicketFilesOut(**await service.ticket_files(member_id=user.id, ticket_id=ticket_id))


@router.delete(
    "/tickets/{ticket_id}/files/{file_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Take a document off a ticket (the document stays in the project)",
)
async def detach_file(ticket_id: str, file_id: str, user: UserDep, service: ServiceDep) -> Response:
    await service.detach_file(member_id=user.id, ticket_id=ticket_id, file_id=file_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/tickets/{ticket_id}/comments",
    status_code=status.HTTP_201_CREATED,
    response_model=CommentOut,
    summary="Comment on a ticket",
)
async def add_comment(
    ticket_id: str, payload: CommentIn, user: UserDep, service: ServiceDep
) -> CommentOut:
    return CommentOut(
        **await service.add_comment(member_id=user.id, ticket_id=ticket_id, body=payload.body)
    )


@router.get(
    "/activity",
    response_model=list[TicketEventOut],
    summary="Changes and updates (one project, or every project you can see)",
)
async def activity(
    user: UserDep,
    service: ServiceDep,
    project_id: Annotated[
        str | None, Query(description="One project; omit for all of yours")
    ] = None,
    ticket_id: Annotated[str | None, Query(description="Only this ticket's events")] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> list[TicketEventOut]:
    rows = await service.activity(
        member_id=user.id, project_id=project_id, ticket_id=ticket_id, limit=limit
    )
    return [TicketEventOut(**row) for row in rows]
