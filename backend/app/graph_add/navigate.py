"""Decide where a new document belongs: score every folder locally, then rank.

No model is called. Each folder's description, its name and the names it holds are compared with
the document's own vocabulary (see :mod:`app.graph_add.scoring`), using the same weights Graph AI
Search uses — so the folders offered are the folders a search would look in.

The scan is exhaustive rather than a walk: scoring a few hundred folders costs nothing, and a
parent folder with a vague description must not hide a child that is a perfect match. Every score
comes from one function, so the ordering needs no consolidation call.

The module is free of database and transport concerns: callers pass briefs, which keeps it
testable with plain dataclasses.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field

from app.core.text import Query, ScoreConfig, score_folder_texts, terms

#: Folders offered to the caller (the project root may add one more).
MAX_CANDIDATES = 3
#: The floor for being offered at all. It is deliberately low — unlike Graph AI Search, which
#: prunes a walk and must be frugal, placement ranks the whole tree and then shows the best few,
#: so the floor only has to exclude folders that share nothing with the document.
DEFAULT_FOLDER_THRESHOLD = 0.05

ROOT_REASON = "Put the document at the project root."


@dataclass(frozen=True)
class ChildBrief:
    """One folder, as the scanner sees it."""

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
class RankedLocation:
    """One suggested home for the document."""

    node: ChildBrief
    score: float
    reason: str
    folder_names: tuple[str, ...] = ()
    matched: tuple[str, ...] = ()


@dataclass
class Scan:
    """Outcome of scoring the tree: the ranked locations plus what it cost."""

    locations: list[RankedLocation] = field(default_factory=list)
    scored: int = 0
    threshold: float = DEFAULT_FOLDER_THRESHOLD
    scorer_version: str = ""

    def as_dict(self) -> dict[str, object]:
        """Serialisable summary, stored on the request row for debugging."""
        return {
            "folders_scored": self.scored,
            "threshold": self.threshold,
            "scorer_version": self.scorer_version,
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
    """A folder name derived from the document name, offered as a starting point."""
    stem = re.sub(r"\.[^.]+$", "", file_name).strip()
    cleaned = re.sub(r"[-_]+", " ", stem).strip()
    return (cleaned[:60],) if cleaned else ()


def score_folders(
    *,
    folders: Sequence[ChildBrief],
    query: Query,
    file_name: str,
    root_id: str,
    threshold: float = DEFAULT_FOLDER_THRESHOLD,
    max_candidates: int = MAX_CANDIDATES,
    config: ScoreConfig | None = None,
) -> Scan:
    """Score every folder against the document and return the best few, plus the root."""
    config = config or ScoreConfig()
    scan = Scan(threshold=threshold, scorer_version=config.version)
    ranked: list[RankedLocation] = []

    for folder in folders:
        scan.scored += 1
        score = score_folder_texts(
            query,
            name=folder.name,
            description=folder.description,
            contains=folder.contains,
            config=config,
        )
        if score < threshold:
            continue
        haystack = terms(f"{folder.name} {folder.description} {' '.join(folder.contains)}")
        matched = query.matched(haystack)
        ranked.append(
            RankedLocation(
                node=folder,
                score=score,
                reason=_reason(matched),
                folder_names=fallback_folder_names(file_name),
                matched=matched,
            )
        )

    ranked.sort(key=lambda item: (-item.score, natural_key(item.node.path)))
    locations = ranked[:max_candidates]

    root = next((folder for folder in folders if folder.directory_id == root_id), None)
    if root is not None and all(item.node.directory_id != root_id for item in locations):
        locations.append(
            RankedLocation(
                node=root,
                score=0.0,
                reason=ROOT_REASON,
                folder_names=fallback_folder_names(file_name),
            )
        )

    scan.locations = locations
    return scan


def _reason(matched: Sequence[str]) -> str:
    if not matched:
        return "Shares the document's vocabulary."
    return f"Matches {', '.join(matched)}."
