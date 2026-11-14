"""Decide where a new document belongs: a bounded, semantic walk of the existing tree.

The walk starts at the project root and only descends into child folders the navigator
judges relevant, so a large tree costs a handful of model calls rather than one per folder.
A node becomes a *candidate* when it is a leaf, or when none of its children relate to the
document (or the search budget runs out). The root is always offered as a final option.

Per-level relevance only orders the walk. The final ordering comes from one consolidation
call, because scores produced in separate model calls are not comparable with each other.

The module is deliberately free of database and transport concerns: callers pass lookup
callables, which keeps the traversal unit-testable with plain dicts.
"""

from __future__ import annotations

import heapq
import itertools
import logging
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Protocol

logger = logging.getLogger(__name__)

#: Model calls that may be spent descending. Bounds cost and latency on huge trees.
MAX_EXPANSIONS = 8
#: Child folders descended into from any single node.
MAX_BRANCH = 3
#: Candidates returned to the caller (the root may add one more).
MAX_CANDIDATES = 3

ROOT_REASON = "Put the document at the project root."
LEAF_REASON = "Folder with nothing below it."
NO_MATCH_REASON = "No folder directly inside relates to this document."
BUDGET_REASON = "Search budget reached before descending."
DEGRADED_REASON = "Matching failed, so this folder was kept as a fallback."


@dataclass(frozen=True)
class ChildBrief:
    """One folder, as the navigator sees it.

    ``contains`` lists a few names of what sits directly inside. Stored descriptions can be
    generic ("team guides"), and the names are the cheapest signal that a folder is the right
    branch — the model sees them, and the offline mock relies on them.
    """

    directory_id: str
    path: str
    name: str
    depth: int
    description: str
    direct_file_count: int = 0
    child_directory_count: int = 0
    contains: tuple[str, ...] = ()

    @property
    def is_leaf(self) -> bool:
        return self.child_directory_count == 0


@dataclass(frozen=True)
class CandidateContext:
    """A candidate folder plus the files directly inside it (ranking context)."""

    node: ChildBrief
    files: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class Judgement:
    """What the navigator thinks of one child folder at one level."""

    directory_id: str
    relevance: float
    reason: str = ""


@dataclass(frozen=True)
class RankedCandidate:
    """Final placement of one candidate in the consolidation ranking."""

    directory_id: str
    score: float
    reason: str = ""
    folder_names: tuple[str, ...] = ()


class Navigator(Protocol):
    """What the walk needs from a navigator (Gemini or the offline mock)."""

    model_name: str

    async def summarise_file(self, *, name: str, text: str) -> str: ...

    async def judge_children(
        self,
        *,
        file_name: str,
        summary: str,
        path: str,
        children: Sequence[ChildBrief],
    ) -> Sequence[Judgement]: ...

    async def rank(
        self,
        *,
        file_name: str,
        summary: str,
        candidates: Sequence[CandidateContext],
    ) -> Sequence[RankedCandidate]: ...

    async def describe_folder(
        self,
        *,
        path: str,
        files: Sequence[tuple[str, str]],
        directories: Sequence[tuple[str, str]],
    ) -> str: ...


@dataclass(frozen=True)
class RankedLocation:
    """One suggested add location, ready to be presented to the user."""

    node: ChildBrief
    score: float
    reason: str
    folder_names: tuple[str, ...] = ()
    budget_exhausted: bool = False


@dataclass
class Traversal:
    """Outcome of the walk: ranked locations plus what it cost."""

    locations: list[RankedLocation] = field(default_factory=list)
    expanded: int = 0
    visited: int = 0
    degraded: bool = False
    budget_exhausted: bool = False

    def as_dict(self, model: str) -> dict[str, object]:
        """Serialisable summary, stored on the request row for debugging."""
        return {
            "expanded": self.expanded,
            "visited": self.visited,
            "degraded": self.degraded,
            "budget_exhausted": self.budget_exhausted,
            "model": model,
        }


def natural_key(value: str) -> tuple:
    """Case-insensitive, number-aware sort key (``file2`` before ``file10``)."""
    key: list[tuple[int, object]] = []
    for part in re.split(r"(\d+)", value):
        if not part:
            continue
        key.append((0, int(part)) if part.isdigit() else (1, part.casefold()))
    return tuple(key)


def fallback_folder_names(file_name: str) -> tuple[str, ...]:
    """A folder name derived from the document name, when the model offers none."""
    stem = re.sub(r"\.[^.]+$", "", file_name).strip()
    cleaned = re.sub(r"[-_]+", " ", stem).strip()
    return (cleaned[:60],) if cleaned else ()


async def find_add_locations(
    *,
    root: ChildBrief,
    children_of: Callable[[str], Sequence[ChildBrief]],
    files_of: Callable[[str], Sequence[tuple[str, str]]] | None,
    summary: str,
    file_name: str,
    navigator: Navigator,
    max_expansions: int = MAX_EXPANSIONS,
    max_branch: int = MAX_BRANCH,
    max_candidates: int = MAX_CANDIDATES,
) -> Traversal:
    """Walk the tree and return the ranked places the document could go."""
    traversal = Traversal()
    counter = itertools.count()
    frontier: list[tuple[float, tuple, int, ChildBrief]] = [
        (-1.0, natural_key(root.path), next(counter), root)
    ]
    seen: set[str] = {root.directory_id}
    # The root has no parent judgement, so its own relevance is 0.0 — the heap priority
    # below is what makes it get expanded first.
    scores: dict[str, float] = {root.directory_id: 0.0}
    reasons: dict[str, str] = {root.directory_id: ROOT_REASON}
    found: list[tuple[ChildBrief, str, float, bool]] = []

    while frontier:
        _, _, _, node = heapq.heappop(frontier)
        traversal.visited += 1
        children = list(children_of(node.directory_id))

        if not children:
            reason = reasons.get(node.directory_id, LEAF_REASON)
            found.append((node, reason, scores[node.directory_id], False))
            continue

        if traversal.expanded >= max_expansions:
            traversal.budget_exhausted = True
            found.append((node, BUDGET_REASON, scores.get(node.directory_id, 0.0), True))
            continue

        traversal.expanded += 1
        try:
            judged = await navigator.judge_children(
                file_name=file_name,
                summary=summary,
                path=node.path,
                children=children,
            )
        except Exception as exc:  # noqa: BLE001 - one bad node must not sink the request
            logger.warning("Could not judge children of %r: %s", node.path or "<root>", exc)
            traversal.degraded = True
            found.append((node, DEGRADED_REASON, scores.get(node.directory_id, 0.0), False))
            continue

        by_id = {child.directory_id: child for child in children}
        matches = [
            judgement
            for judgement in judged
            if judgement.directory_id in by_id and judgement.relevance > 0
        ]
        if not matches:
            found.append((node, NO_MATCH_REASON, scores.get(node.directory_id, 0.0), False))
            continue

        matches.sort(key=lambda item: (-item.relevance, natural_key(by_id[item.directory_id].path)))
        for judgement in matches[:max_branch]:
            child = by_id[judgement.directory_id]
            if child.directory_id in seen:
                continue
            seen.add(child.directory_id)
            scores[child.directory_id] = judgement.relevance
            reasons[child.directory_id] = judgement.reason or "Related folder."
            heapq.heappush(
                frontier,
                (-judgement.relevance, natural_key(child.path), next(counter), child),
            )

    if not found:  # defensive: a tree that produced no candidate at all
        found.append((root, ROOT_REASON, scores[root.directory_id], False))

    contexts = [
        CandidateContext(
            node=node,
            files=tuple(files_of(node.directory_id)) if files_of else (),
        )
        for node, _, _, _ in found
    ]

    ranked: dict[str, RankedCandidate] = {}
    if len(contexts) > 1:
        known = {context.node.directory_id for context in contexts}
        try:
            for item in await navigator.rank(
                file_name=file_name, summary=summary, candidates=contexts
            ):
                if item.directory_id in known and 0.0 <= item.score <= 1.0:
                    ranked[item.directory_id] = item
        except Exception as exc:  # noqa: BLE001 - fall back to the per-level scores
            logger.warning("Could not rank add locations: %s", exc)
            traversal.degraded = True
            ranked.clear()

    locations: list[RankedLocation] = []
    for node, reason, score, exhausted in found:
        item = ranked.get(node.directory_id)
        if item is not None:
            locations.append(
                RankedLocation(
                    node=node,
                    score=item.score,
                    reason=item.reason or reason,
                    folder_names=item.folder_names or fallback_folder_names(file_name),
                    budget_exhausted=exhausted,
                )
            )
        else:
            locations.append(
                RankedLocation(
                    node=node,
                    score=score if not ranked else 0.0,
                    reason=reason,
                    folder_names=fallback_folder_names(file_name),
                    budget_exhausted=exhausted,
                )
            )

    locations.sort(key=lambda item: (-item.score, natural_key(item.node.path)))
    top = locations[:max_candidates]
    if not any(item.node.directory_id == root.directory_id for item in top):
        top.append(
            RankedLocation(
                node=root,
                score=0.0,
                reason=ROOT_REASON,
                folder_names=fallback_folder_names(file_name),
            )
        )

    traversal.locations = top
    return traversal
