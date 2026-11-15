"""Adapters between the calendar and the sections that own the things it can point at.

The calendar may not import another section's internals, so:

* ticket deadlines come through :mod:`app.tickets.public` — read-only, model-free, and never
  copied into a calendar table;
* an event's notes may mention a document or folder (:mod:`app.graph_creation.public`) or a
  ticket (:mod:`app.tickets.public`), offered by the picker and validated before the event is
  written.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from typing import Any

from app.core.mentions import Mention
from app.graph_creation import public as graph_section
from app.tickets import public as tickets_section


def _rank(label: str, path: str, needle: str) -> int:
    """A shared ordering for the merged picker list: name prefix, name, path, then rest."""
    if not needle:
        return 0
    lowered = label.casefold()
    if lowered.startswith(needle):
        return 0
    if needle in lowered:
        return 1
    return 2 if needle in path.casefold() else 3


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


class MentionCatalogueAdapter:
    """Implements :class:`app.calendar.service.MentionCatalogue` over the public modules.

    Events themselves are deliberately absent: an event's notes point at the things a meeting is
    about, not at another meeting (chat is where events get mentioned).
    """

    async def search(self, *, project_id: str, query: str, limit: int) -> list[dict[str, Any]]:
        needle = (query or "").casefold()
        documents = await graph_section.search_targets(
            project_id=project_id, query=query, limit=limit
        )
        tickets = await tickets_section.search_targets(
            project_id=project_id, query=query, limit=limit
        )

        merged = [*documents, *tickets]
        merged.sort(
            key=lambda item: (
                _rank(str(item.get("label") or ""), str(item.get("path") or ""), needle),
                0 if item.get("kind") != tickets_section.TICKET else 1,
                str(item.get("label") or "").casefold(),
            )
        )
        return merged[:limit]

    async def describe(
        self, *, project_id: str, mentions: Sequence[Mention]
    ) -> dict[tuple[str, str], dict[str, Any]]:
        refs = [(mention.kind, mention.id) for mention in mentions]
        documents = await graph_section.describe_targets(project_id=project_id, refs=refs)
        tickets = await tickets_section.describe_targets(project_id=project_id, refs=refs)
        return {**documents, **tickets}
