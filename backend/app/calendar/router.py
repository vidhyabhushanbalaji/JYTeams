"""HTTP routes for the Calendar section.

Mounted at ``/api/calendar``.

* ``GET /personal?from=&to=`` — the individual calendar: my own events, the events of every
  project I am in, and the deadlines of the tickets assigned to me.
* ``GET /projects/{id}?from=&to=`` — one project's calendar: its events and **every** ticket
  deadline in it.
* ``POST /events``, ``PATCH /events/{id}``, ``DELETE /events/{id}`` — events. A body with
  ``project_id`` is a project event; without it, a personal one.

Deadlines are read live from the tickets section, so nothing here is stale and no model is called.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from app.calendar.adapters import TicketDeadlineSource
from app.calendar.repository import SupabaseCalendarRepository
from app.calendar.schemas import CalendarOut, EventIn, EventOut, EventPatch
from app.calendar.service import CalendarService
from app.core.access import SupabaseProjectAccess
from app.core.auth import CurrentUser, get_current_user

router = APIRouter(tags=["Calendar"])


def get_service() -> CalendarService:
    """Wire the service (Supabase events, membership, the tickets deadline source)."""
    return CalendarService(
        repository=SupabaseCalendarRepository(),
        access=SupabaseProjectAccess(),
        deadlines=TicketDeadlineSource(),
    )


ServiceDep = Annotated[CalendarService, Depends(get_service)]
UserDep = Annotated[CurrentUser, Depends(get_current_user)]

RangeStart = Annotated[date, Query(alias="from", description="First day, inclusive")]
RangeEnd = Annotated[date, Query(alias="to", description="Last day, inclusive")]


@router.get(
    "/personal",
    response_model=CalendarOut,
    summary="My calendar (my events, my projects' events, my deadlines)",
)
async def personal(
    user: UserDep, service: ServiceDep, start: RangeStart, end: RangeEnd
) -> CalendarOut:
    return CalendarOut(**await service.personal(member_id=user.id, start=start, end=end))


@router.get(
    "/projects/{project_id}",
    response_model=CalendarOut,
    summary="One project's calendar (its events and every ticket deadline)",
)
async def project(
    project_id: str, user: UserDep, service: ServiceDep, start: RangeStart, end: RangeEnd
) -> CalendarOut:
    return CalendarOut(
        **await service.project(member_id=user.id, project_id=project_id, start=start, end=end)
    )


@router.post(
    "/events",
    status_code=status.HTTP_201_CREATED,
    response_model=EventOut,
    summary="Add an event (project event when project_id is set, otherwise personal)",
)
async def create_event(payload: EventIn, user: UserDep, service: ServiceDep) -> EventOut:
    return EventOut(**await service.create_event(member_id=user.id, payload=payload))


@router.patch(
    "/events/{event_id}",
    response_model=EventOut,
    summary="Edit an event (only the person who added it)",
)
async def update_event(
    event_id: str, payload: EventPatch, user: UserDep, service: ServiceDep
) -> EventOut:
    return EventOut(
        **await service.update_event(member_id=user.id, event_id=event_id, payload=payload)
    )


@router.delete(
    "/events/{event_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove an event (only the person who added it)",
)
async def delete_event(event_id: str, user: UserDep, service: ServiceDep) -> Response:
    await service.delete_event(member_id=user.id, event_id=event_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
