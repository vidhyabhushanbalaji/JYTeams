"""Find documents by walking the tree, guided by the stored summaries.

The agreed rule: start at the root, log every child file whose summary matches the query,
and recurse into every child folder whose description matches, until the frontier is empty.
There is deliberately **no expansion budget** — the walk exhausts itself — so the cost is
proportional to how much of the tree the model considers relevant.

Two things keep that honest:

* ``max_directories`` is an *optional* valve. Leaving it unset means unbounded; setting it
  stops the walk and reports ``budget_exhausted``.
* when the walk logs nothing and the project is small (``FALLBACK_MAX_PROJECT_FILES``), every
  folder is swept once, so a folder with a vague description cannot hide its files.

Ranking happens once at the end, in batches when the log is large, because scores produced
in separate model calls are not comparable with each other.

The module holds no database or transport code: callers pass lookup callables, which keeps
the walk unit-testable with plain dictionaries.
"""

from __future__ import annotations

import heapq
import itertools
import logging
import re
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass, field
from typing import Protocol

logger = logging.getLogger(__name__)

#: Documents ranked per model call. Must stay **at least** the maximum result count the API
#: allows (25), so the consolidation pass can never drop a document a caller could ask for.
RANK_BATCH = 25
#: Projects at or below this many documents get the whole-tree fallback sweep.
FALLBACK_MAX_PROJECT_FILES = 40


@dataclass(frozen=True)
class DocumentBrief:
    """One file, as the search sees it."""

    file_id: str
    name: str
    path: str
    directory_id: str
    directory_path: str
    summary: str


@dataclass(frozen=True)
class FolderBrief:
    """One folder: its description plus a few names of what it holds."""

    directory_id: str
    path: str
    name: str
    depth: int
    description: str
    contains: tuple[str, ...] = ()
    direct_file_count: int = 0
    child_directory_count: int = 0


@dataclass(frozen=True)
class DocumentMatch:
    """A file the searcher judged relevant, and why."""

    file_id: str
    relevance: float
    reason: str = ""


@dataclass(frozen=True)
class FolderMatch:
    """A subfolder the searcher judged worth opening, and why."""

    directory_id: str
    relevance: float
    reason: str = ""


@dataclass(frozen=True)
class FolderVerdicts:
    """Everything one folder's turn in the walk produced."""

    documents: tuple[DocumentMatch, ...] = ()
    folders: tuple[FolderMatch, ...] = ()


@dataclass(frozen=True)
class LoggedFile:
    """A file logged during the walk, with the relevance that got it there."""

    document: DocumentBrief
    relevance: float
    reason: str = ""


@dataclass(frozen=True)
class FileRank:
    """Where the consolidation call placed one logged file."""

    file_id: str
    score: float
    reason: str = ""


@dataclass(frozen=True)
class RankedFile:
    """A final result."""

    document: DocumentBrief
    score: float
    reason: str


class Searcher(Protocol):
    """What the walk needs from a searcher (Gemini or the offline mock)."""

    model_name: str

    async def judge(
        self,
        *,
        query: str,
        folder: FolderBrief,
        documents: Sequence[DocumentBrief],
        folders: Sequence[FolderBrief],
    ) -> FolderVerdicts: ...

    async def rank(self, *, query: str, documents: Sequence[LoggedFile]) -> Sequence[FileRank]: ...


@dataclass
class SearchOutcome:
    """The ranked results plus what the walk cost."""

    results: list[RankedFile] = field(default_factory=list)
    opened: list[str] = field(default_factory=list)
    visited: int = 0
    documents_considered: int = 0
    fallback_used: bool = False
    degraded: bool = False
    budget_exhausted: bool = False
    model: str = ""

    def traversal(self) -> dict[str, object]:
        """Serialisable summary for the response."""
        return {
            "directories_visited": self.visited,
            "directories_opened": len(self.opened),
            "documents_considered": self.documents_considered,
            "fallback_used": self.fallback_used,
            "degraded": self.degraded,
            "budget_exhausted": self.budget_exhausted,
            "model": self.model,
        }


def natural_key(value: str) -> tuple:
    """Case-insensitive, number-aware sort key (``file2`` before ``file10``)."""
    key: list[tuple[int, object]] = []
    for part in re.split(r"(\d+)", value):
        if not part:
            continue
        key.append((0, int(part)) if part.isdigit() else (1, part.casefold()))
    return tuple(key)


def all_folders(
    root: FolderBrief, children_of: Callable[[str], Sequence[FolderBrief]]
) -> Iterator[FolderBrief]:
    """Every folder in the tree, root first (used by the fallback sweep)."""
    yield root
    for child in children_of(root.directory_id):
        yield from all_folders(child, children_of)


def _log(logged: dict[str, LoggedFile], document: DocumentBrief, match: DocumentMatch) -> None:
    """Keep the best relevance seen for a file."""
    if match.relevance <= 0:
        return
    previous = logged.get(document.file_id)
    if previous is None or match.relevance > previous.relevance:
        logged[document.file_id] = LoggedFile(
            document=document,
            relevance=min(1.0, match.relevance),
            reason=match.reason or "Matched the query.",
        )


def _apply_ranks(documents: Sequence[LoggedFile], ranks: Sequence[FileRank]) -> list[RankedFile]:
    """Pair the model's ranking with the documents it was shown."""
    by_id = {item.document.file_id: item for item in documents}
    seen: set[str] = set()
    ranked: list[RankedFile] = []
    for rank in ranks:
        item = by_id.get(rank.file_id)
        if item is None or rank.file_id in seen:
            continue
        seen.add(rank.file_id)
        ranked.append(
            RankedFile(
                document=item.document,
                score=min(1.0, max(0.0, rank.score)),
                reason=rank.reason or item.reason,
            )
        )
    # A document the model forgot is kept at the bottom rather than silently dropped.
    ranked.extend(
        RankedFile(document=item.document, score=0.0, reason=item.reason)
        for item in documents
        if item.document.file_id not in seen
    )
    return ranked


async def _rank(
    *,
    query: str,
    documents: Sequence[LoggedFile],
    searcher: Searcher,
    batch_size: int,
) -> list[RankedFile]:
    """Rank the log, batching large logs and consolidating the winners."""
    batches = [
        list(documents[start : start + batch_size])
        for start in range(0, len(documents), batch_size)
    ]
    if len(batches) == 1:
        return _apply_ranks(batches[0], await searcher.rank(query=query, documents=batches[0]))

    scored: list[RankedFile] = []
    for batch in batches:
        scored.extend(_apply_ranks(batch, await searcher.rank(query=query, documents=batch)))
    scored.sort(key=lambda item: (-item.score, natural_key(item.document.path)))

    finalists = scored[:batch_size]
    if len(finalists) <= 1:
        return finalists
    # Batch scores are not comparable, so the survivors get one final pass.
    final_documents = [LoggedFile(item.document, item.score, item.reason) for item in finalists]
    return _apply_ranks(
        final_documents, await searcher.rank(query=query, documents=final_documents)
    )


async def find_matching_files(
    *,
    root: FolderBrief,
    documents_of: Callable[[str], Sequence[DocumentBrief]],
    children_of: Callable[[str], Sequence[FolderBrief]],
    query: str,
    searcher: Searcher,
    total_documents: int,
    max_directories: int | None = None,
    fallback_limit: int = FALLBACK_MAX_PROJECT_FILES,
    batch_size: int = RANK_BATCH,
) -> SearchOutcome:
    """Walk the tree, log the matching files, and rank them against the query."""
    outcome = SearchOutcome(model=searcher.model_name)
    logged: dict[str, LoggedFile] = {}
    counter = itertools.count()
    frontier: list[tuple[float, tuple, int, FolderBrief]] = [
        (-1.0, natural_key(root.path), next(counter), root)
    ]
    seen: set[str] = {root.directory_id}

    while frontier:
        if max_directories is not None and len(outcome.opened) >= max_directories:
            outcome.budget_exhausted = True
            logger.info("Stopped after %s folders (max_directories)", len(outcome.opened))
            break

        _, _, _, folder = heapq.heappop(frontier)
        outcome.visited += 1
        documents = list(documents_of(folder.directory_id))
        folders = list(children_of(folder.directory_id))
        outcome.documents_considered += len(documents)

        try:
            verdicts = await searcher.judge(
                query=query, folder=folder, documents=documents, folders=folders
            )
        except Exception as exc:  # noqa: BLE001 - one bad folder must not sink the search
            logger.warning("Could not search %r: %s", folder.path or "<root>", exc)
            outcome.degraded = True
            continue

        outcome.opened.append(folder.path)
        by_file = {item.file_id: item for item in documents}
        for match in verdicts.documents:
            document = by_file.get(match.file_id)
            if document is not None:
                _log(logged, document, match)

        by_folder = {item.directory_id: item for item in folders}
        for match in verdicts.folders:
            child = by_folder.get(match.directory_id)
            if child is None or match.relevance <= 0 or child.directory_id in seen:
                continue
            seen.add(child.directory_id)
            heapq.heappush(
                frontier,
                (-match.relevance, natural_key(child.path), next(counter), child),
            )

    # The sweep is the safety net for a vague description, not a second budget: a caller who
    # asked for a bounded walk must not get an unbounded one behind their back.
    if (
        not logged
        and max_directories is None
        and total_documents
        and (total_documents <= fallback_limit)
    ):
        await _fallback(
            root=root,
            documents_of=documents_of,
            children_of=children_of,
            query=query,
            searcher=searcher,
            outcome=outcome,
            logged=logged,
        )

    documents = sorted(
        logged.values(), key=lambda item: (-item.relevance, natural_key(item.document.path))
    )
    if not documents:
        return outcome

    try:
        ranked = await _rank(
            query=query, documents=documents, searcher=searcher, batch_size=batch_size
        )
    except Exception as exc:  # noqa: BLE001 - fall back to the per-folder relevance
        logger.warning("Could not rank search results: %s", exc)
        outcome.degraded = True
        ranked = [
            RankedFile(document=item.document, score=item.relevance, reason=item.reason)
            for item in documents
        ]

    ranked.sort(key=lambda item: (-item.score, natural_key(item.document.path)))
    outcome.results = ranked
    return outcome


async def _fallback(
    *,
    root: FolderBrief,
    documents_of: Callable[[str], Sequence[DocumentBrief]],
    children_of: Callable[[str], Sequence[FolderBrief]],
    query: str,
    searcher: Searcher,
    outcome: SearchOutcome,
    logged: dict[str, LoggedFile],
) -> None:
    """Sweep every folder once: small projects cannot afford a hidden branch."""
    outcome.fallback_used = True
    already = set(outcome.opened)
    for folder in all_folders(root, children_of):
        if folder.path in already:
            continue
        documents = list(documents_of(folder.directory_id))
        outcome.documents_considered += len(documents)
        if not documents:
            continue
        try:
            verdicts = await searcher.judge(
                query=query, folder=folder, documents=documents, folders=[]
            )
        except Exception as exc:  # noqa: BLE001 - the sweep is best effort
            logger.warning("Fallback sweep failed at %r: %s", folder.path, exc)
            outcome.degraded = True
            continue
        outcome.opened.append(folder.path)
        by_file = {item.file_id: item for item in documents}
        for match in verdicts.documents:
            document = by_file.get(match.file_id)
            if document is not None:
                _log(logged, document, match)
