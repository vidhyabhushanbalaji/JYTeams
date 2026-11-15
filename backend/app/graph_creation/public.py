"""The public surface of Graph Creation — the only module another section may import.

Chat offers a composer's ``@`` suggestions and validates the mentions a message carries. Both need
the names, ids and paths of a project's documents and folders — read-only, no model call, no
write. Everything else here (services, tree building, storage) stays internal to the section.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from app.graph_creation.repository import SupabaseGraphRepository

#: How many suggestions one query returns at most.
TARGET_LIMIT = 20
#: The hard ceiling, so a caller cannot ask for the whole tree in one picker.
MAX_TARGET_LIMIT = 50

Target = dict[str, Any]
Ref = tuple[str, str]
#: The kinds this section can describe; chat's other mention kind (ticket) belongs to tickets.
FILE = "file"
DIRECTORY = "directory"


def parent_path(path: str) -> str:
    """The folder part of a document's path (``guides/auth.md`` -> ``guides``)."""
    clean = (path or "").strip("/")
    if "/" not in clean:
        return ""
    return clean.rsplit("/", 1)[0]


def _rank(name: str, path: str, needle: str) -> int:
    """0 = the name starts with the query, 1 = it contains it, 2 = only the path does."""
    if not needle:
        return 0
    lowered_name = name.casefold()
    if lowered_name.startswith(needle):
        return 0
    if needle in lowered_name:
        return 1
    return 2 if needle in path.casefold() else 3


def _file_target(row: dict[str, Any]) -> Target:
    path = str(row.get("path") or "")
    return {
        "kind": FILE,
        "id": str(row["id"]),
        "label": str(row.get("name") or path.rsplit("/", 1)[-1] or "document"),
        "path": path,
        "directory_path": parent_path(path),
        "ticket_number": None,
        "detail": "document",
    }


def _directory_target(row: dict[str, Any]) -> Target:
    path = str(row.get("path") or "")
    return {
        "kind": DIRECTORY,
        "id": str(row["id"]),
        "label": str(row.get("name") or path.rsplit("/", 1)[-1] or "folder"),
        "path": path,
        "directory_path": path,
        "ticket_number": None,
        "detail": "folder",
    }


async def search_targets(*, project_id: str, query: str, limit: int = TARGET_LIMIT) -> list[Target]:
    """Documents and folders of one project that match ``query`` (names first, then paths)."""
    repository = SupabaseGraphRepository()
    files = await repository.list_files(project_id)
    directories = await repository.list_directories(project_id)

    needle = " ".join((query or "").split()).casefold()
    candidates: list[tuple[int, str, Target]] = []
    for row in files:
        target = _file_target(row)
        rank = _rank(target["label"], target["path"], needle)
        if rank < 3:
            candidates.append((rank, target["label"].casefold(), target))
    for row in directories:
        target = _directory_target(row)
        rank = _rank(target["label"], target["path"], needle)
        if rank < 3:
            candidates.append((rank, target["label"].casefold(), target))

    candidates.sort(key=lambda item: (item[0], item[1], item[2]["path"].casefold()))
    return [target for _, _, target in candidates[: max(1, min(limit, MAX_TARGET_LIMIT))]]


async def describe_targets(*, project_id: str, refs: Sequence[Ref]) -> dict[Ref, Target]:
    """Resolve ``(kind, id)`` references that belong to this project.

    A ref that is unknown, of another kind, or from another project is simply absent from the
    result — the caller decides that a missing mention is a refused message.
    """
    wanted = {ref for ref in refs if ref[0] in {FILE, DIRECTORY}}
    if not wanted:
        return {}

    repository = SupabaseGraphRepository()
    found: dict[Ref, Target] = {}
    file_ids = {ref[1] for ref in wanted if ref[0] == FILE}
    directory_ids = {ref[1] for ref in wanted if ref[0] == DIRECTORY}

    if file_ids:
        for row in await repository.list_files(project_id):
            key = (FILE, str(row["id"]))
            if key in wanted:
                found[key] = _file_target(row)
    if directory_ids:
        for row in await repository.list_directories(project_id):
            key = (DIRECTORY, str(row["id"]))
            if key in wanted:
                found[key] = _directory_target(row)

    return found
