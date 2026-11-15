"""Adapters between chat and the sections that own the things it mentions.

Chat may not import another section's internals, so both edges go through the owning section's
public module: :mod:`app.graph_creation.public` (documents, folders) and
:mod:`app.tickets.public` (tickets). Both are read-only and make no model call.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from app.chat.mentions import Mention
from app.graph_creation import public as graph_section
from app.tickets import public as ticket_section


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


class MentionCatalogueAdapter:
    """Implements :class:`app.chat.service.MentionCatalogue` over the two public modules."""

    async def search(self, *, project_id: str, query: str, limit: int) -> list[dict[str, Any]]:
        needle = (query or "").casefold()
        documents = await graph_section.search_targets(
            project_id=project_id, query=query, limit=limit
        )
        tickets = await ticket_section.search_targets(
            project_id=project_id, query=query, limit=limit
        )

        merged = [*documents, *tickets]
        merged.sort(
            key=lambda item: (
                _rank(str(item.get("label") or ""), str(item.get("path") or ""), needle),
                0 if item.get("kind") != ticket_section.TICKET else 1,
                str(item.get("label") or "").casefold(),
            )
        )
        return merged[:limit]

    async def describe(
        self, *, project_id: str, mentions: Sequence[Mention]
    ) -> dict[tuple[str, str], dict[str, Any]]:
        refs = [(mention.kind, mention.id) for mention in mentions]
        documents = await graph_section.describe_targets(project_id=project_id, refs=refs)
        tickets = await ticket_section.describe_targets(project_id=project_id, refs=refs)
        return {**documents, **tickets}
