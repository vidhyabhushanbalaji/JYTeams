"""Orchestration for the Chat section.

A project's group chat already exists — the project *is* the channel — so this service only has
to: check membership (:class:`app.core.access.ProjectAccess`), resolve any mention markers in a
message against that project before storing it, and hand back messages in chronological order.

Mentions are resolved once, at post time, and stored denormalised on the row. Nothing here calls
a model, and nothing writes to a project tree.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any, Protocol

from fastapi import HTTPException, status

from app.chat.mentions import MAX_MENTIONS, Mention, extract
from app.chat.repository import ChatRepository, Row
from app.core.access import ProjectAccess, ProjectRole

logger = logging.getLogger(__name__)

#: What a deleted message's body becomes. The row (and its ``seq``) stays, so pollers never gap.
DELETED_BODY = "[deleted]"

DEFAULT_LIMIT = 50
MAX_LIMIT = 200
MAX_TARGETS = 20


class MentionCatalogue(Protocol):
    """What chat needs from the sections that own documents, folders, tickets and events."""

    async def search(self, *, project_id: str, query: str, limit: int) -> list[dict[str, Any]]: ...

    async def describe(
        self, *, project_id: str, mentions: Sequence[Mention]
    ) -> dict[tuple[str, str], dict[str, Any]]: ...


def _author(row: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if not row:
        return None
    return {"id": str(row["id"]), "display_name": str(row.get("display_name") or "Member")}


def _mention_out(value: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "kind": str(value.get("kind") or ""),
        "id": str(value.get("id") or ""),
        "label": str(value.get("label") or "item"),
        "path": str(value.get("path") or ""),
        "directory_path": str(value.get("directory_path") or ""),
        "ticket_number": value.get("ticket_number"),
        "event_day": value.get("event_day"),
    }


def _message_out(
    row: Mapping[str, Any], authors: Mapping[str, Mapping[str, Any]]
) -> dict[str, Any]:
    member_id = str(row.get("member_id") or "")
    return {
        "seq": int(row.get("seq") or 0),
        "id": str(row["id"]),
        "project_id": str(row["project_id"]),
        "author": _author(authors.get(member_id)),
        "body": str(row.get("body") or ""),
        "mentions": [_mention_out(item) for item in (row.get("mentions") or [])],
        "created_at": row.get("created_at"),
        "deleted": str(row.get("body") or "") == DELETED_BODY,
    }


class ChatService:
    """Messages, channels and mention targets for the caller's projects."""

    def __init__(
        self, *, repository: ChatRepository, access: ProjectAccess, catalogue: MentionCatalogue
    ) -> None:
        self._repository = repository
        self._access = access
        self._catalogue = catalogue

    # ---------------------------------------------------------------- channels

    async def channels(self, member_id: str) -> list[dict[str, Any]]:
        """Every project the caller can see, as a chat, with its last message."""
        project_ids = await self._access.project_ids(member_id)
        projects = await self._repository.list_projects_by_ids(project_ids)
        names = {str(row["id"]): str(row.get("name") or "Project") for row in projects}

        latest: dict[str, Row] = {}
        for project_id in project_ids:
            row = await self._repository.latest_message(project_id)
            if row is not None:
                latest[project_id] = row

        authors = await self._authors_for(list(latest.values()))
        channels = [
            {
                "project_id": project_id,
                "project_name": names.get(project_id, "Project"),
                "last_message": (
                    _message_out(latest[project_id], authors) if project_id in latest else None
                ),
                "last_activity_at": (
                    latest[project_id].get("created_at") if project_id in latest else None
                ),
            }
            for project_id in project_ids
        ]
        channels.sort(
            key=lambda item: (
                item["last_activity_at"] is None,
                _descending_time(item["last_activity_at"]),
                item["project_name"].casefold(),
            )
        )
        return channels

    # ---------------------------------------------------------------- messages

    async def messages(
        self,
        *,
        member_id: str,
        project_id: str,
        after_seq: int | None = None,
        limit: int = DEFAULT_LIMIT,
    ) -> list[dict[str, Any]]:
        """One page of a project's chat: the newest page, or everything after a cursor."""
        await self._access.require(project_id, member_id)
        rows = await self._repository.list_messages(
            project_id=project_id, after_seq=after_seq, limit=_clamp_limit(limit)
        )
        return await self._describe(rows)

    async def post_message(self, *, member_id: str, project_id: str, body: str) -> dict[str, Any]:
        """Store a message, resolving and validating its mention markers first."""
        await self._access.require(project_id, member_id)

        text = (body or "").strip()
        if not text:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="a message needs some text"
            )

        mentions = extract(text)
        if len(mentions) > MAX_MENTIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"a message may mention at most {MAX_MENTIONS} things",
            )

        resolved = await self._resolve(project_id, mentions)
        payload: Row = {
            "project_id": project_id,
            "member_id": member_id,
            "body": text,
            "mentions": [_mention_out(resolved[mention.key]) for mention in mentions],
        }
        row = await self._repository.insert_message(payload)
        authors = await self._authors_for([row])
        return _message_out(row, authors)

    async def delete_message(self, *, member_id: str, message_id: str) -> None:
        """Remove a message's text. The author may; so may the project's owner."""
        row = await self._repository.get_message(message_id)
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found.")
        project_id = str(row["project_id"])
        role = await self._access.require(project_id, member_id)
        if str(row.get("member_id") or "") != member_id and role is not ProjectRole.OWNER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the author or the project owner can delete this message.",
            )
        if str(row.get("body") or "") == DELETED_BODY:
            return
        await self._repository.update_message(message_id, {"body": DELETED_BODY, "mentions": []})

    # ---------------------------------------------------------------- mentions

    async def mention_targets(
        self, *, member_id: str, project_id: str, query: str, limit: int = MAX_TARGETS
    ) -> list[dict[str, Any]]:
        """What the composer may offer after an `@`: documents, folders, tickets and events."""
        await self._access.require(project_id, member_id)
        cleaned = " ".join((query or "").split())[:120]
        rows = await self._catalogue.search(
            project_id=project_id, query=cleaned, limit=max(1, min(limit, 50))
        )
        return [
            {
                "kind": str(row.get("kind") or ""),
                "id": str(row.get("id") or ""),
                "label": str(row.get("label") or "item"),
                "path": str(row.get("path") or ""),
                "directory_path": str(row.get("directory_path") or ""),
                "ticket_number": row.get("ticket_number"),
                "event_day": row.get("event_day"),
                "detail": str(row.get("detail") or ""),
            }
            for row in rows
        ]

    # --------------------------------------------------------------- internals

    async def _resolve(
        self, project_id: str, mentions: Sequence[Mention]
    ) -> dict[tuple[str, str], dict[str, Any]]:
        """Every mention must resolve inside the message's project, or the post is refused."""
        if not mentions:
            return {}
        found = await self._catalogue.describe(project_id=project_id, mentions=mentions)
        wanted = {mention.key for mention in mentions}
        missing = [
            f"{mention.kind}:{mention.id}" for mention in mentions if mention.key not in found
        ]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="these mentions are not part of this project: " + ", ".join(sorted(missing)),
            )
        return {key: value for key, value in found.items() if key in wanted}

    async def _describe(self, rows: Sequence[Row]) -> list[dict[str, Any]]:
        authors = await self._authors_for(rows)
        return [_message_out(row, authors) for row in rows]

    async def _authors_for(self, rows: Sequence[Row]) -> dict[str, Mapping[str, Any]]:
        member_ids = sorted({str(row.get("member_id") or "") for row in rows} - {""})
        if not member_ids:
            return {}
        members = await self._repository.list_members_by_ids(member_ids)
        return {str(row["id"]): row for row in members}


def _clamp_limit(value: int) -> int:
    return max(1, min(int(value or DEFAULT_LIMIT), MAX_LIMIT))


def _descending_time(value: Any) -> float:
    """A sort key that puts newer activity first."""
    if not isinstance(value, str) or not value:
        return 0.0
    try:
        return -datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0
