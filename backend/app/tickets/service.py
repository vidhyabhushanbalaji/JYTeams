"""Orchestration for the Tickets section.

Three things live here:

* **identity** — a member is a name. Signing in finds or creates one; there is no password.
* **tickets** — create, assign, describe, complete, comment, and the files attached to them.
* **the cached search** — a ticket's files come from Graph AI Search, run the first time the
  ticket is opened and stored on the ticket row. One model call first reduces the ticket's
  wording to a short search query (:mod:`app.tickets.distill`), because a search scores by term
  coverage and a ticket written for people is mostly words no document contains. The query is
  re-distilled only when the ticket's words change; the (model-free) search re-runs when the
  project's documents change or when the user presses Refresh.

Access is project membership (:class:`app.core.access.ProjectAccess`), never ``owner_id``: a
shared project is fully usable by every member. Events are written through
:class:`app.core.activity.ActivityLog` so the feed also carries changes that did not come from a
ticket (an upload, a document save, a placement).
"""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime
from typing import Any, Protocol

from fastapi import HTTPException, status

from app.core.access import ProjectAccess, ProjectRole
from app.core.activity import (
    FILE_ATTACHED,
    FILE_DETACHED,
    PROJECT_MEMBER_REMOVED,
    PROJECT_SHARED,
    TICKET_ASSIGNED,
    TICKET_COMMENTED,
    TICKET_COMPLETED,
    TICKET_CREATED,
    TICKET_REOPENED,
    TICKET_STATUS_CHANGED,
    TICKET_UPDATED,
    ActivityLog,
)
from app.core.config import Settings
from app.tickets.cache import (
    FILE_LIMIT,
    fingerprint,
    search_query,
    terms_fingerprint,
)
from app.tickets.distill import SearchTerms, TicketDistiller, context_from, searchable
from app.tickets.repository import Row, TicketRepository
from app.tickets.schemas import (
    Priority,
    TicketCreateIn,
    TicketStatus,
    TicketUpdateIn,
)

logger = logging.getLogger(__name__)

MAX_LABEL_CHARS = 30
MAX_LABELS = 10
_COMMENT_PREVIEW = 140
_DONE = TicketStatus.DONE.value
_PRIORITY_RANK = {Priority.HIGH.value: 0, Priority.MEDIUM.value: 1, Priority.LOW.value: 2}


class TicketSearch(Protocol):
    """What the tickets section needs from Graph AI Search (no model call, read-only)."""

    async def search(
        self,
        *,
        project_id: str,
        member_id: str,
        query: str,
        context: str,
        limit: int,
    ) -> dict[str, Any]: ...


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _name_key(display_name: str) -> str:
    return " ".join((display_name or "").split()).lower()


def _due_date(value: object) -> date | None:
    """A ``date`` from a PostgREST date string (or a date), so responses are consistent."""
    if isinstance(value, date):
        return value
    if isinstance(value, str) and value:
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


def _member_out(row: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if not row:
        return None
    return {"id": str(row["id"]), "display_name": str(row.get("display_name") or "Member")}


def _labels(values: Sequence[str]) -> list[str]:
    """Normalise labels: trimmed, deduplicated, capped."""
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in values:
        label = " ".join((value or "").split())
        if not label:
            continue
        if len(label) > MAX_LABEL_CHARS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"a label is longer than {MAX_LABEL_CHARS} characters",
            )
        key = label.casefold()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(label)
    if len(cleaned) > MAX_LABELS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"a ticket may carry at most {MAX_LABELS} labels",
        )
    return cleaned


class TicketService:
    """Tickets, their files, and the people they belong to."""

    def __init__(
        self,
        *,
        repository: TicketRepository,
        access: ProjectAccess,
        activity: ActivityLog,
        search: TicketSearch,
        distiller: TicketDistiller,
        settings: Settings,
    ) -> None:
        self._repository = repository
        self._access = access
        self._activity = activity
        self._search = search
        self._distiller = distiller
        self._settings = settings

    # ------------------------------------------------------------------ members

    async def sign_in(self, display_name: str) -> Row:
        """Find the member with this name, or create them. No password, by design."""
        cleaned = " ".join((display_name or "").split())
        if not cleaned or len(cleaned) > 60:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="a name needs 1 to 60 characters",
            )
        existing = await self._repository.find_member(_name_key(cleaned))
        if existing is not None:
            return existing
        return await self._repository.create_member(cleaned)

    async def current_member(self, member_id: str) -> Row:
        """The member behind the caller's identity, or 404 so the app offers the name picker."""
        member = await self._repository.get_member(member_id)
        if member is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="This identity is not a member yet. Pick a name to continue.",
            )
        return member

    async def list_members(self) -> list[Row]:
        return await self._repository.list_members()

    # ----------------------------------------------------------------- sharing

    async def list_project_members(self, project_id: str, member_id: str) -> list[dict[str, Any]]:
        await self._require_project(project_id, member_id)
        return [
            {
                "id": str(row["member_id"]),
                "display_name": str(row.get("display_name") or "Member"),
                "role": str(row.get("role") or "member"),
                "added_at": row.get("added_at"),
            }
            for row in await self._repository.list_project_members(project_id)
        ]

    async def share_project(self, project_id: str, member_id: str, target_id: str) -> Row:
        """Add a member to a project. Only the project's owner may do this."""
        project = await self._require_owner(project_id, member_id)
        target = await self._repository.get_member(target_id)
        if target is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found.")
        current = {
            str(row["member_id"]) for row in await self._repository.list_project_members(project_id)
        }
        if target_id in current:
            return target
        await self._repository.add_project_member(
            project_id=project_id, member_id=target_id, role="member", added_by=member_id
        )
        await self._record(
            project_id=project_id,
            member_id=member_id,
            kind=PROJECT_SHARED,
            detail={
                "member_id": target_id,
                "member_name": str(target.get("display_name") or ""),
                "project_name": str(project.get("name") or ""),
            },
        )
        return target

    async def unshare_project(self, project_id: str, member_id: str, target_id: str) -> None:
        """Remove a member. The owner cannot remove themselves."""
        project = await self._require_owner(project_id, member_id)
        if str(project.get("owner_id")) == target_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The project's owner cannot be removed from it.",
            )
        target = await self._repository.get_member(target_id)
        removed = await self._repository.remove_project_member(project_id, target_id)
        if not removed:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="That member does not have access to this project.",
            )
        await self._record(
            project_id=project_id,
            member_id=member_id,
            kind=PROJECT_MEMBER_REMOVED,
            detail={
                "member_id": target_id,
                "member_name": str((target or {}).get("display_name") or ""),
                "project_name": str(project.get("name") or ""),
            },
        )

    # ------------------------------------------------------------------ tickets

    async def list_tickets(
        self,
        *,
        member_id: str,
        scope: str = "mine",
        project_id: str | None = None,
        status_filter: str | None = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        """`mine` is the caller's own to-do list; `project` is everything on one project."""
        if scope not in {"mine", "project"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="scope must be 'mine' or 'project'",
            )
        if status_filter is not None and status_filter not in {item.value for item in TicketStatus}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"unknown status {status_filter!r}",
            )
        if scope == "project" and not project_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="project_id is required when scope=project",
            )

        if project_id:
            await self._require_project(project_id, member_id)
            project_ids = [project_id]
        else:
            project_ids = await self._access.project_ids(member_id)

        rows = await self._repository.list_tickets(
            project_ids=project_ids,
            assignee_id=member_id if scope == "mine" else None,
            status=status_filter,
            limit=limit,
        )
        return self._sorted(await self._describe_tickets(rows))

    @staticmethod
    def _sorted(tickets: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Open tickets first, then by due date, then priority — the order a to-do list wants."""

        def key(ticket: dict[str, Any]) -> tuple[Any, ...]:
            due = str(ticket.get("due_date") or "9999-12-31")
            return (
                1 if ticket.get("status") == _DONE else 0,
                due,
                _PRIORITY_RANK.get(str(ticket.get("priority")), 1),
                str(ticket.get("created_at") or ""),
            )

        return sorted(tickets, key=key)

    async def create_ticket(self, *, member_id: str, payload: TicketCreateIn) -> dict[str, Any]:
        project = await self._require_project(payload.project_id, member_id)
        assignee_id = payload.assignee_id or member_id
        await self._require_project_member(project["id"], assignee_id)

        title = " ".join(payload.title.split())
        row = await self._repository.create_ticket(
            {
                "project_id": project["id"],
                "number": await self._repository.next_ticket_number(project["id"]),
                "title": title,
                "description": payload.description or "",
                "status": TicketStatus.TODO.value,
                "priority": payload.priority.value,
                "due_date": payload.due_date.isoformat() if payload.due_date else None,
                "labels": _labels(payload.labels),
                "assignee_id": assignee_id,
                "reporter_id": member_id,
                "created_at": _now(),
                "updated_at": _now(),
            }
        )
        assignee = await self._repository.get_member(assignee_id)
        await self._record(
            project_id=project["id"],
            member_id=member_id,
            ticket_id=str(row["id"]),
            kind=TICKET_CREATED,
            detail={
                "number": int(row["number"]),
                "title": title,
                "assignee_id": assignee_id,
                "assignee_name": str((assignee or {}).get("display_name") or ""),
                "project_name": str(project.get("name") or ""),
            },
        )
        described = await self._describe_tickets([row])
        return described[0]

    async def get_ticket(
        self, *, member_id: str, ticket_id: str, refresh: bool = False
    ) -> dict[str, Any]:
        """One ticket with its comments and its files (which runs the cached search once)."""
        ticket = await self._require_ticket(ticket_id, member_id)
        files, ticket = await self._files_for(ticket, member_id=member_id, refresh=refresh)
        described = (await self._describe_tickets([ticket]))[0]
        return {
            **described,
            "comments": await self._describe_comments(ticket_id),
            "files": files,
        }

    async def update_ticket(
        self, *, member_id: str, ticket_id: str, payload: TicketUpdateIn
    ) -> dict[str, Any]:
        """Apply the fields that were sent. A `null` assignee clears it."""
        ticket = await self._require_ticket(ticket_id, member_id)
        fields: dict[str, Any] = {}
        changed: list[str] = []

        supplied = payload.supplied()
        if "title" in supplied:
            title = " ".join((payload.title or "").split())
            if not title:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="a ticket needs a title",
                )
            if title != ticket.get("title"):
                fields["title"] = title
                changed.append("title")

        if "description" in supplied:
            description = payload.description or ""
            if description != (ticket.get("description") or ""):
                fields["description"] = description
                changed.append("description")

        if "assignee_id" in supplied:
            assignee_id = payload.assignee_id
            if assignee_id:
                await self._require_project_member(str(ticket["project_id"]), assignee_id)
            if str(ticket.get("assignee_id") or "") != (assignee_id or ""):
                fields["assignee_id"] = assignee_id
                changed.append("assignee")

        if (
            "priority" in supplied
            and payload.priority is not None
            and payload.priority.value != ticket.get("priority")
        ):
            fields["priority"] = payload.priority.value
            changed.append("priority")

        if "due_date" in supplied:
            due = payload.due_date.isoformat() if payload.due_date else None
            if due != ticket.get("due_date"):
                fields["due_date"] = due
                changed.append("due_date")

        if "labels" in supplied and payload.labels is not None:
            labels = _labels(payload.labels)
            if labels != list(ticket.get("labels") or []):
                fields["labels"] = labels
                changed.append("labels")

        if not fields:
            return (await self._describe_tickets([ticket]))[0]

        fields["updated_at"] = _now()
        row = await self._repository.update_ticket(ticket_id, fields)
        project_id = str(row["project_id"])

        if "assignee" in changed:
            assignee = (
                await self._repository.get_member(str(fields["assignee_id"]))
                if fields.get("assignee_id")
                else None
            )
            await self._record(
                project_id=project_id,
                member_id=member_id,
                ticket_id=ticket_id,
                kind=TICKET_ASSIGNED,
                detail={
                    "number": int(row["number"]),
                    "assignee_id": fields.get("assignee_id"),
                    "assignee_name": str((assignee or {}).get("display_name") or ""),
                },
            )
        rest = [field for field in changed if field != "assignee"]
        if rest:
            await self._record(
                project_id=project_id,
                member_id=member_id,
                ticket_id=ticket_id,
                kind=TICKET_UPDATED,
                detail={"number": int(row["number"]), "fields": rest},
            )
        return (await self._describe_tickets([row]))[0]

    async def set_status(
        self, *, member_id: str, ticket_id: str, new_status: TicketStatus
    ) -> dict[str, Any]:
        """Move a ticket; ticking the completion box sets `done` and stamps who did it."""
        ticket = await self._require_ticket(ticket_id, member_id)
        current = str(ticket.get("status") or TicketStatus.TODO.value)
        target = new_status.value
        if current == target:
            return (await self._describe_tickets([ticket]))[0]

        fields: dict[str, Any] = {"status": target, "updated_at": _now()}
        if target == _DONE:
            fields["completed_at"] = _now()
            fields["completed_by"] = member_id
        else:
            fields["completed_at"] = None
            fields["completed_by"] = None

        row = await self._repository.update_ticket(ticket_id, fields)
        if target == _DONE:
            kind = TICKET_COMPLETED
        elif current == _DONE:
            kind = TICKET_REOPENED
        else:
            kind = TICKET_STATUS_CHANGED
        await self._record(
            project_id=str(row["project_id"]),
            member_id=member_id,
            ticket_id=ticket_id,
            kind=kind,
            detail={
                "number": int(row["number"]),
                "title": str(row.get("title") or ""),
                "from": current,
                "to": target,
            },
        )
        return (await self._describe_tickets([row]))[0]

    # -------------------------------------------------------------------- files

    async def ticket_files(
        self, *, member_id: str, ticket_id: str, refresh: bool = False
    ) -> dict[str, Any]:
        """The ticket's documents: search suggestions (cached) plus the attached ones."""
        ticket = await self._require_ticket(ticket_id, member_id)
        files, _ = await self._files_for(ticket, member_id=member_id, refresh=refresh)
        return files

    async def attach_file(
        self,
        *,
        member_id: str,
        ticket_id: str,
        file_id: str,
        source: str = "existing",
    ) -> dict[str, Any]:
        """Put a document that already lives in the project on the ticket."""
        ticket = await self._require_ticket(ticket_id, member_id)
        project_id = str(ticket["project_id"])
        file = await self._repository.get_file(file_id)
        if file is None or str(file.get("project_id")) != project_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="That document is not part of this project.",
            )

        existing = {
            str(row["file_id"]) for row in await self._repository.list_attachments(ticket_id)
        }
        if file_id in existing:
            return await self._attached_one(ticket_id, file_id)

        await self._repository.add_attachment(
            ticket_id=ticket_id,
            file_id=file_id,
            added_by=member_id,
            source=source if source in {"upload", "existing"} else "existing",
        )
        directories = await self._repository.list_directories(project_id)
        directory_paths = {str(row["id"]): str(row.get("path") or "") for row in directories}
        await self._record(
            project_id=project_id,
            member_id=member_id,
            ticket_id=ticket_id,
            kind=FILE_ATTACHED,
            detail={
                "number": int(ticket["number"]),
                "file_id": file_id,
                "file_name": str(file.get("name") or ""),
                "path": str(file.get("path") or ""),
                "directory_path": directory_paths.get(str(file.get("directory_id")), ""),
                "source": source,
            },
        )
        return await self._attached_one(ticket_id, file_id)

    async def detach_file(self, *, member_id: str, ticket_id: str, file_id: str) -> None:
        """Take a document off the ticket. The document itself stays in the project."""
        ticket = await self._require_ticket(ticket_id, member_id)
        file = await self._repository.get_file(file_id)
        removed = await self._repository.remove_attachment(ticket_id, file_id)
        if not removed:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="That document is not attached to this ticket.",
            )
        await self._record(
            project_id=str(ticket["project_id"]),
            member_id=member_id,
            ticket_id=ticket_id,
            kind=FILE_DETACHED,
            detail={
                "number": int(ticket["number"]),
                "file_id": file_id,
                "file_name": str((file or {}).get("name") or ""),
            },
        )

    async def add_comment(self, *, member_id: str, ticket_id: str, body: str) -> dict[str, Any]:
        ticket = await self._require_ticket(ticket_id, member_id)
        text = (body or "").strip()
        if not text:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="a comment cannot be empty"
            )
        row = await self._repository.create_comment(
            ticket_id=ticket_id, author_id=member_id, body=text
        )
        author = await self._repository.get_member(member_id)
        await self._record(
            project_id=str(ticket["project_id"]),
            member_id=member_id,
            ticket_id=ticket_id,
            kind=TICKET_COMMENTED,
            detail={
                "number": int(ticket["number"]),
                "excerpt": text[:_COMMENT_PREVIEW],
            },
        )
        return {
            "id": str(row["id"]),
            "body": text,
            "author": _member_out(author),
            "created_at": row.get("created_at"),
        }

    # ------------------------------------------------------------------ activity

    async def activity(
        self,
        *,
        member_id: str,
        project_id: str | None = None,
        ticket_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """The changes-and-updates feed: one project, or every project the member can see."""
        if project_id:
            await self._require_project(project_id, member_id)
            project_ids = [project_id]
        else:
            project_ids = await self._access.project_ids(member_id)

        rows = await self._repository.list_events(
            project_ids=project_ids, ticket_id=ticket_id, limit=max(1, min(limit, 200))
        )
        actors = {
            str(member["id"]): member
            for member in await self._repository.get_members_by_ids(
                sorted({str(row["member_id"]) for row in rows if row.get("member_id")})
            )
        }
        numbers = {
            str(ticket["id"]): int(ticket["number"])
            for ticket in await self._repository.get_tickets_by_ids(
                sorted({str(row["ticket_id"]) for row in rows if row.get("ticket_id")})
            )
        }
        return [
            {
                "id": str(row["id"]),
                "kind": str(row["kind"]),
                "detail": dict(row.get("detail") or {}),
                "project_id": str(row["project_id"]),
                "ticket_id": row.get("ticket_id"),
                "ticket_number": numbers.get(str(row.get("ticket_id") or "")),
                "actor": _member_out(actors.get(str(row.get("member_id") or ""))),
                "created_at": row.get("created_at"),
            }
            for row in rows
        ]

    # ------------------------------------------------------------------- helpers

    async def _describe_tickets(self, rows: list[Row]) -> list[dict[str, Any]]:
        """Turn ticket rows into the shapes the client renders, with names and counts filled in."""
        if not rows:
            return []
        projects = {
            str(project["id"]): str(project.get("name") or "")
            for project in await self._repository.list_projects_by_ids(
                sorted({str(row["project_id"]) for row in rows})
            )
        }
        counts = await self._repository.list_ticket_counts([str(row["id"]) for row in rows])
        members = {
            str(member["id"]): member
            for member in await self._repository.get_members_by_ids(
                sorted(
                    {
                        str(row[key])
                        for row in rows
                        for key in ("assignee_id", "reporter_id", "completed_by")
                        if row.get(key)
                    }
                )
            )
        }

        described: list[dict[str, Any]] = []
        for row in rows:
            ticket_id = str(row["id"])
            attachments, comments = counts.get(ticket_id, (0, 0))
            described.append(
                {
                    "id": ticket_id,
                    "project_id": str(row["project_id"]),
                    "project_name": projects.get(str(row["project_id"]), ""),
                    "number": int(row["number"]),
                    "title": str(row.get("title") or ""),
                    "description": str(row.get("description") or ""),
                    "status": str(row.get("status") or TicketStatus.TODO.value),
                    "priority": str(row.get("priority") or Priority.MEDIUM.value),
                    "due_date": _due_date(row.get("due_date")),
                    "labels": [str(item) for item in (row.get("labels") or [])],
                    "assignee": _member_out(members.get(str(row.get("assignee_id") or ""))),
                    "reporter": _member_out(members.get(str(row.get("reporter_id") or ""))),
                    "completed_at": row.get("completed_at"),
                    "completed_by": _member_out(members.get(str(row.get("completed_by") or ""))),
                    "attachment_count": attachments,
                    "comment_count": comments,
                    "created_at": row.get("created_at"),
                    "updated_at": row.get("updated_at"),
                }
            )
        return described

    async def _describe_comments(self, ticket_id: str) -> list[dict[str, Any]]:
        rows = await self._repository.list_comments(ticket_id)
        authors = {
            str(member["id"]): member
            for member in await self._repository.get_members_by_ids(
                sorted({str(row["author_id"]) for row in rows if row.get("author_id")})
            )
        }
        return [
            {
                "id": str(row["id"]),
                "body": str(row.get("body") or ""),
                "author": _member_out(authors.get(str(row.get("author_id") or ""))),
                "created_at": row.get("created_at"),
            }
            for row in rows
        ]

    async def _files_for(
        self, ticket: Row, *, member_id: str, refresh: bool = False
    ) -> tuple[dict[str, Any], Row]:
        """The ticket's documents, running the cached search only when it is needed.

        Two caches decide the work. The **terms** cost one model call, re-made only when the
        ticket's own words change (``terms_fingerprint``); the **results** are the model-free walk,
        re-made when those terms or the project's documents change, or when ``refresh`` is set.
        A model that cannot answer never stops a ticket from opening: the ticket's own words are
        searched instead, and the next open asks the model again.
        """
        project_id = str(ticket["project_id"])
        ticket_id = str(ticket["id"])
        title = str(ticket.get("title") or "")
        description = str(ticket.get("description") or "")
        files = await self._repository.list_files(project_id)
        directories = await self._repository.list_directories(project_id)
        directory_paths = {str(row["id"]): str(row.get("path") or "") for row in directories}

        terms_stamp = terms_fingerprint(title=title, description=description)
        terms_changed = ticket.get("search_terms_fingerprint") != terms_stamp
        query = str(ticket.get("search_query") or "")
        context = str(ticket.get("search_context") or "")
        reason: str | None = None
        settled = not terms_changed

        if terms_changed:
            distilled = await self._distil(title=title, description=description)
            if distilled is not None and searchable(distilled):
                query, context = distilled.query, context_from(distilled)
                settled = True
            else:
                query, context, reason = search_query(title, description)
                # "Nothing here to search for" is settled; a model that failed is not, so the
                # next open tries it again rather than being stuck on the fallback.
                settled = reason is not None

        stamp = fingerprint(
            query=query,
            context=context,
            files=files,
            limit=FILE_LIMIT,
            folder_threshold=self._settings.scoring_folder_threshold,
        )
        cached = list(ticket.get("search_results") or [])
        stale = bool(cached) and ticket.get("search_fingerprint") != stamp

        if query and (refresh or not cached or stale):
            try:
                body = await self._search.search(
                    project_id=project_id,
                    member_id=member_id,
                    query=query,
                    context=context,
                    limit=FILE_LIMIT,
                )
            except HTTPException as exc:
                # A project with no tree yet (or a query the search refuses) must not make the
                # ticket unopenable: show the reason and keep the rest of the ticket.
                if exc.status_code not in {
                    status.HTTP_400_BAD_REQUEST,
                    status.HTTP_409_CONFLICT,
                }:
                    raise
                reason = str(exc.detail)
                cached = []
                stale = False
                if terms_changed and settled:
                    ticket = await self._store_terms(
                        ticket_id, query=query, context=context, stamp=terms_stamp
                    )
            else:
                cached = [self._hit(item) for item in body.get("results", [])][:FILE_LIMIT]
                fields: Row = {
                    "search_results": cached,
                    "search_fingerprint": stamp,
                    "search_refreshed_at": _now(),
                }
                if terms_changed and settled:
                    # The cold path writes both caches in one update.
                    fields.update(
                        {
                            "search_query": query,
                            "search_context": context,
                            "search_terms_fingerprint": terms_stamp,
                        }
                    )
                ticket = await self._repository.update_ticket(ticket_id, fields)
                stale = False
        elif terms_changed and settled:
            # Nothing to search for (an empty project, or a ticket with only filler words).
            ticket = await self._store_terms(
                ticket_id, query=query, context=context, stamp=terms_stamp
            )

        alive = {str(row["id"]) for row in files}
        kept: list[dict[str, Any]] = []
        for hit in cached:
            file_id = str(hit.get("file_id") or "")
            if file_id not in alive:
                stale = True
                continue
            kept.append({**hit, "directory_path": hit.get("directory_path") or ""})
        if not query:
            kept, stale = [], False

        payload = {
            "query": query,
            "context": context,
            "suggested": kept,
            "attached": await self._attached(ticket_id, files, directory_paths),
            "cached_at": ticket.get("search_refreshed_at"),
            "stale": stale,
            "reason": reason,
        }
        return payload, ticket

    async def _distil(self, *, title: str, description: str) -> SearchTerms | None:
        """The ticket's search terms, or ``None`` when the distiller produced nothing usable."""
        try:
            return await self._distiller.terms(title=title, description=description)
        except Exception:  # noqa: BLE001 - a model outage must not make a ticket unopenable
            logger.warning(
                "Could not distil the ticket %r; searching its own words instead", title[:80]
            )
            return None

    async def _store_terms(self, ticket_id: str, *, query: str, context: str, stamp: str) -> Row:
        """Store the distilled query without touching the cached results."""
        return await self._repository.update_ticket(
            ticket_id,
            {
                "search_query": query,
                "search_context": context,
                "search_terms_fingerprint": stamp,
            },
        )

    async def _attached(
        self, ticket_id: str, files: Sequence[Row], directory_paths: Mapping[str, str]
    ) -> list[dict[str, Any]]:
        rows = await self._repository.list_attachments(ticket_id)
        by_id = {str(row["id"]): row for row in files}
        members = {
            str(member["id"]): member
            for member in await self._repository.get_members_by_ids(
                sorted({str(row["added_by"]) for row in rows if row.get("added_by")})
            )
        }
        attached: list[dict[str, Any]] = []
        for row in rows:
            file = by_id.get(str(row["file_id"]))
            if file is None:
                continue
            attached.append(
                {
                    "file_id": str(file["id"]),
                    "name": str(file.get("name") or ""),
                    "path": str(file.get("path") or ""),
                    "directory_path": directory_paths.get(str(file.get("directory_id")), ""),
                    "size_bytes": int(file.get("size_bytes") or 0),
                    "added_at": row.get("added_at"),
                    "added_by": _member_out(members.get(str(row.get("added_by") or ""))),
                    "source": str(row.get("source") or "existing"),
                }
            )
        return attached

    async def _attached_one(self, ticket_id: str, file_id: str) -> dict[str, Any]:
        ticket = await self._repository.get_ticket(ticket_id)
        files = await self._repository.list_files(str(ticket["project_id"])) if ticket else []
        directories = (
            await self._repository.list_directories(str(ticket["project_id"])) if ticket else []
        )
        directory_paths = {str(row["id"]): str(row.get("path") or "") for row in directories}
        for item in await self._attached(ticket_id, files, directory_paths):
            if item["file_id"] == file_id:
                return item
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="That document is not attached."
        )

    @staticmethod
    def _hit(item: Mapping[str, Any]) -> dict[str, Any]:
        """Keep only what the ticket shows from a search hit."""
        return {
            "file_id": str(item.get("file_id") or ""),
            "name": str(item.get("name") or ""),
            "path": str(item.get("path") or ""),
            "directory_id": str(item.get("directory_id") or ""),
            "directory_path": str(item.get("directory_path") or ""),
            "score": float(item.get("score") or 0.0),
            "matched_terms": [str(term) for term in (item.get("matched_terms") or [])],
            "excerpt": str(item.get("excerpt") or ""),
        }

    async def _record(
        self,
        *,
        project_id: str,
        member_id: str,
        kind: str,
        detail: Mapping[str, Any] | None = None,
        ticket_id: str | None = None,
    ) -> None:
        """Write an activity row. The log never fails the action that produced it."""
        try:
            await self._activity.record(
                project_id=project_id,
                member_id=member_id,
                kind=kind,
                detail=detail,
                ticket_id=ticket_id,
            )
        except Exception:  # noqa: BLE001 - an audit row must not break the request
            logger.warning("Could not record %s for project %s", kind, project_id)

    async def _require_project(self, project_id: str, member_id: str) -> Row:
        await self._access.require(project_id, member_id)
        project = await self._repository.get_project(project_id)
        if project is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
        return project

    async def _require_owner(self, project_id: str, member_id: str) -> Row:
        role = await self._access.require(project_id, member_id)
        if role is not ProjectRole.OWNER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the project's owner can change who it is shared with.",
            )
        return await self._require_project(project_id, member_id)

    async def _require_ticket(self, ticket_id: str, member_id: str) -> Row:
        ticket = await self._repository.get_ticket(ticket_id)
        if ticket is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found.")
        await self._access.require(str(ticket["project_id"]), member_id)
        return ticket

    async def _require_project_member(self, project_id: str, member_id: str) -> None:
        if await self._access.role(project_id, member_id) is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="That person is not a member of this project.",
            )
