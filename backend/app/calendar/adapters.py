"""Adapter between the calendar and the tickets section.

The calendar may not import another section's internals, so deadlines come through
:mod:`app.tickets.public` — read-only, model-free, and never copied into a calendar table.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from typing import Any

from app.tickets import public as tickets_section


class TicketDeadlineSource:
    """Implements :class:`app.calendar.service.DeadlineSource` with the tickets section."""

    async def list_deadlines(
        self,
        *,
        project_ids: Sequence[str],
        assignee_id: str | None,
        start: date,
        end: date,
    ) -> list[dict[str, Any]]:
        return await tickets_section.list_deadlines(
            project_ids=project_ids,
            assignee_id=assignee_id,
            start=start,
            end=end,
        )
