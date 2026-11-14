"""Find documents by walking the tree, scored locally — no model calls.

The shape is the one Graph AI Search already had: start at the root, log the files whose content
matches the query, and open every child folder whose description matches, until the frontier is
empty. What changed is *who decides*: a deterministic scorer (:mod:`app.graph_ai_search.scoring`,
built on :mod:`app.core.text`) replaces the per-folder model call, so a search costs no prompts
and no quota.

Descriptions are the cheap index — opening a branch costs one comparison over rows already in
memory — while document bodies are the expensive part, so a body is read only for a folder that
was actually opened. Three things bound that:

* ``folder_threshold`` prunes a branch whose description shares nothing with the query;
* ``max_files_read`` caps how many documents one search may open;
* ``max_directories`` is the optional valve a caller can use to stop the walk early.

Scores from one scorer are comparable by construction, so the old consolidation call is gone:
ranking is a sort. The module holds no database, storage or transport code — callers pass lookup
callables and a ``read_body`` coroutine, which keeps the walk testable with plain dictionaries.
"""

from __future__ import annotations

import heapq
import itertools
import logging
import re
from collections.abc import Awaitable, Callable, Iterator, Sequence
from dataclasses import dataclass, field
from typing import Protocol

from app.core.text import Query, excerpt

logger = logging.getLogger(__name__)

#: Folder relevance at or above this opens the branch. With the default weights this means
#: "the description covers roughly a third of the query, or the names inside nearly cover it".
DEFAULT_FOLDER_THRESHOLD = 0.2
#: Below this, a search has only weak matches, so a small project gets the sweep. Descriptions
#: cannot mention every technology a branch holds, and a branch wrongly pruned hides its files.
WEAK_MATCH_THRESHOLD = 0.5
#: Documents one search may open, so a cold cache cannot turn into hundreds of downloads.
MAX_FILES_READ = 200
#: Projects at or below this many documents get the whole-tree sweep when nothing matched.
FALLBACK_MAX_PROJECT_FILES = 40
#: Characters of a matching document returned as evidence.
EXCERPT_CHARS = 200


@dataclass(frozen=True)
class DocumentBrief:
    """One file, as the search sees it: identity plus where its bytes live."""

    file_id: str
    name: str
    path: str
    directory_id: str
    directory_path: str
    storage_bucket: str = ""
    storage_path: str = ""
    content_sha256: str = ""


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
class FolderScore:
    """The scorer's verdict on one folder."""

    score: float
    matched: tuple[str, ...] = ()


@dataclass(frozen=True)
class DocumentScore:
    """The scorer's verdict on one document."""

    score: float
    matched: tuple[str, ...] = ()


class Scorer(Protocol):
    """What the walk needs from a scorer (the real one, or a scripted one in tests)."""

    version: str

    def score_folder(self, query: Query, folder: FolderBrief) -> FolderScore: ...

    def score_document(self, query: Query, document: DocumentBrief, body: str) -> DocumentScore: ...


@dataclass(frozen=True)
class FolderMatch:
    """A relevant folder, reported so a client can browse instead of guess."""

    directory_id: str
    path: str
    name: str
    depth: int
    score: float
    matched: tuple[str, ...] = ()


@dataclass(frozen=True)
class FileMatch:
    """A document that answers the query, with the evidence that got it there."""

    document: DocumentBrief
    score: float
    matched: tuple[str, ...] = ()
    excerpt: str = ""


@dataclass
class SearchOutcome:
    """The ranked results plus what the walk cost."""

    results: list[FileMatch] = field(default_factory=list)
    directories: list[FolderMatch] = field(default_factory=list)
    opened: list[str] = field(default_factory=list)
    visited: int = 0
    documents_considered: int = 0
    files_read: int = 0
    fallback_used: bool = False
    degraded: bool = False
    budget_exhausted: bool = False
    scorer_version: str = ""

    def traversal(self, *, duration_ms: int = 0) -> dict[str, object]:
        """Serialisable summary for the response."""
        return {
            "directories_visited": self.visited,
            "directories_opened": len(self.opened),
            "documents_considered": self.documents_considered,
            "files_read": self.files_read,
            "fallback_used": self.fallback_used,
            "degraded": self.degraded,
            "budget_exhausted": self.budget_exhausted,
            "scorer_version": self.scorer_version,
            "duration_ms": duration_ms,
        }


#: Reads one document's text; the service supplies this so the walk stays storage-agnostic.
ReadBody = Callable[[DocumentBrief], Awaitable[str]]


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


async def find_matching_files(
    *,
    root: FolderBrief,
    documents_of: Callable[[str], Sequence[DocumentBrief]],
    children_of: Callable[[str], Sequence[FolderBrief]],
    read_body: ReadBody,
    query: Query,
    scorer: Scorer,
    total_documents: int,
    max_directories: int | None = None,
    fallback_limit: int = FALLBACK_MAX_PROJECT_FILES,
    folder_threshold: float = DEFAULT_FOLDER_THRESHOLD,
    weak_match_threshold: float = WEAK_MATCH_THRESHOLD,
    max_files_read: int = MAX_FILES_READ,
) -> SearchOutcome:
    """Walk the tree, score the documents in every opened folder, and rank the matches."""
    outcome = SearchOutcome(scorer_version=scorer.version)
    logged: dict[str, FileMatch] = {}
    folders: dict[str, FolderMatch] = {}
    counter = itertools.count()
    frontier: list[tuple[float, tuple, int, FolderBrief]] = [
        (-1.0, natural_key(root.path), next(counter), root)
    ]
    seen: set[str] = {root.directory_id}

    root_verdict = scorer.score_folder(query, root)
    if root_verdict.score > 0:
        _remember(folders, root, root_verdict, threshold=0.0)

    while frontier:
        if max_directories is not None and len(outcome.opened) >= max_directories:
            outcome.budget_exhausted = True
            logger.info("Stopped after %s folders (max_directories)", len(outcome.opened))
            break

        _, _, _, folder = heapq.heappop(frontier)
        outcome.visited += 1
        outcome.opened.append(folder.path)

        documents = list(documents_of(folder.directory_id))
        outcome.documents_considered += len(documents)

        for child in children_of(folder.directory_id):
            verdict = scorer.score_folder(query, child)
            if verdict.score < folder_threshold:
                continue
            _remember(folders, child, verdict, threshold=folder_threshold)
            if child.directory_id in seen:
                continue
            seen.add(child.directory_id)
            heapq.heappush(
                frontier, (-verdict.score, natural_key(child.path), next(counter), child)
            )

        for document in documents:
            if outcome.files_read >= max_files_read:
                outcome.budget_exhausted = True
                logger.info("Stopped after %s documents (max_files_read)", outcome.files_read)
                break
            await _score_and_log(
                document=document,
                query=query,
                scorer=scorer,
                read_body=read_body,
                outcome=outcome,
                logged=logged,
            )

    # The sweep rescues a search that only found weak matches: a folder description cannot name
    # every technology its branch contains, so a small project must not hide its files behind one
    # vague sentence. It is not a second budget: a caller who asked for a bounded walk keeps a
    # bounded walk.
    best = max((item.score for item in logged.values()), default=0.0)
    if (
        best < weak_match_threshold
        and max_directories is None
        and total_documents
        and total_documents <= fallback_limit
    ):
        await _sweep(
            root=root,
            documents_of=documents_of,
            children_of=children_of,
            read_body=read_body,
            query=query,
            scorer=scorer,
            outcome=outcome,
            logged=logged,
            folders=folders,
            folder_threshold=folder_threshold,
            max_files_read=max_files_read,
        )

    outcome.results = sorted(
        logged.values(), key=lambda item: (-item.score, natural_key(item.document.path))
    )
    outcome.directories = sorted(
        folders.values(), key=lambda item: (-item.score, natural_key(item.path))
    )
    return outcome


async def _sweep(
    *,
    root: FolderBrief,
    documents_of: Callable[[str], Sequence[DocumentBrief]],
    children_of: Callable[[str], Sequence[FolderBrief]],
    read_body: ReadBody,
    query: Query,
    scorer: Scorer,
    outcome: SearchOutcome,
    logged: dict[str, FileMatch],
    folders: dict[str, FolderMatch],
    folder_threshold: float,
    max_files_read: int,
) -> None:
    """Read every folder's documents once: a vague description must not hide a branch."""
    outcome.fallback_used = True
    already = set(outcome.opened)
    for folder in all_folders(root, children_of):
        if folder.path in already:
            continue
        documents = list(documents_of(folder.directory_id))
        outcome.documents_considered += len(documents)
        if not documents:
            continue
        outcome.opened.append(folder.path)
        _remember(folders, folder, scorer.score_folder(query, folder), threshold=folder_threshold)
        for document in documents:
            if outcome.files_read >= max_files_read:
                outcome.budget_exhausted = True
                return
            await _score_and_log(
                document=document,
                query=query,
                scorer=scorer,
                read_body=read_body,
                outcome=outcome,
                logged=logged,
            )


async def _score_and_log(
    *,
    document: DocumentBrief,
    query: Query,
    scorer: Scorer,
    read_body: ReadBody,
    outcome: SearchOutcome,
    logged: dict[str, FileMatch],
) -> None:
    """Read one document, score it against its own text, and keep it if it matches."""
    try:
        body = await read_body(document)
    except Exception as exc:  # noqa: BLE001 - one unreadable file must not sink the search
        logger.warning("Could not read %r: %s", document.path, exc)
        outcome.degraded = True
        return
    outcome.files_read += 1
    verdict = scorer.score_document(query, document, body)
    if verdict.score <= 0:
        return
    previous = logged.get(document.file_id)
    if previous is not None and previous.score >= verdict.score:
        return
    logged[document.file_id] = FileMatch(
        document=document,
        score=min(1.0, verdict.score),
        matched=verdict.matched,
        excerpt=excerpt(body, verdict.matched or query.terms, width=EXCERPT_CHARS),
    )


def _remember(
    target: dict[str, FolderMatch],
    folder: FolderBrief,
    verdict: FolderScore,
    *,
    threshold: float,
) -> None:
    """Keep a folder in the reported list when it clears the threshold."""
    if verdict.score < threshold:
        return
    target[folder.directory_id] = FolderMatch(
        directory_id=folder.directory_id,
        path=folder.path,
        name=folder.name,
        depth=folder.depth,
        score=min(1.0, verdict.score),
        matched=verdict.matched,
    )
