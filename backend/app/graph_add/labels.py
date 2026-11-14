"""Names a new folder or file may use inside an existing tree.

The rules mirror what Graph Creation already stores — a human-readable ``name`` plus a
derived ``ltree`` label, with sibling suffixes keeping labels unique — so a folder created
here is indistinguishable from an uploaded one. They are repeated rather than imported
because a section must not reach into another section's internals.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import PurePosixPath

from app.graph_add.extract import MARKDOWN_SUFFIXES

MAX_FOLDER_NAME = 80
MAX_FILE_NAME = 120
_MAX_LABEL_LENGTH = 80
_SUFFIX_ATTEMPTS = 9
_MAX_SUGGESTIONS = 3


class NameValidationError(ValueError):
    """A folder or file name cannot be used in the tree."""


def validate_folder_name(raw: str) -> str:
    """Return a cleaned folder name, or raise ``NameValidationError``."""
    name = unicodedata.normalize("NFC", (raw or "").strip())
    if not name:
        raise NameValidationError("a folder name is required")
    if len(name) > MAX_FOLDER_NAME:
        raise NameValidationError(f"folder names are limited to {MAX_FOLDER_NAME} characters")
    if name in {".", ".."}:
        raise NameValidationError(f"{name!r} is not a usable folder name")
    if "/" in name or "\\" in name:
        raise NameValidationError("a folder name cannot contain a slash")
    if "\x00" in name:
        raise NameValidationError("invalid character in folder name")
    return name


def validate_file_name(raw: str) -> str:
    """Return a cleaned markdown file name, or raise ``NameValidationError``."""
    name = unicodedata.normalize("NFC", (raw or "").strip())
    if not name:
        raise NameValidationError("a file name is required")
    if len(name) > MAX_FILE_NAME:
        raise NameValidationError(f"file names are limited to {MAX_FILE_NAME} characters")
    if name in {".", ".."}:
        raise NameValidationError(f"{name!r} is not a usable file name")
    if "/" in name or "\\" in name:
        raise NameValidationError("a file name cannot contain a slash")
    if "\x00" in name:
        raise NameValidationError("invalid character in file name")
    if PurePosixPath(name).suffix.lower() not in MARKDOWN_SUFFIXES:
        raise NameValidationError("only markdown files (.md, .markdown, .mdx) can be added")
    return name


def folder_label(name: str) -> str:
    """Map a folder name onto a legal ltree label (lowercase alphanumerics/underscore)."""
    ascii_name = (
        unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii").lower()
    )
    label = re.sub(r"[^a-z0-9_]+", "_", ascii_name).strip("_")
    return (label or "x")[:_MAX_LABEL_LENGTH]


def unique_label(base: str, used: Iterable[str]) -> str:
    """Return ``base`` (or ``base_1``, ``base_2`` …) so sibling labels stay unique."""
    taken = set(used)
    label = base
    suffix = 1
    while label in taken:
        label = f"{base}_{suffix}"
        suffix += 1
    return label


def child_path(parent_path: str, name: str) -> str:
    """Project-relative path of ``name`` inside ``parent_path`` (``""`` is the root)."""
    return f"{parent_path}/{name}" if parent_path else name


def suggested_file_names(name: str, existing: Iterable[str]) -> list[str]:
    """Free alternatives for a clashing file name (``auth-2.md``, ``auth-3.md``, …)."""
    taken = {item.casefold() for item in existing}
    stem = PurePosixPath(name).stem
    suffix = PurePosixPath(name).suffix
    alternatives: list[str] = []
    for attempt in range(2, _SUFFIX_ATTEMPTS + 1):
        candidate = f"{stem}-{attempt}{suffix}"
        if candidate.casefold() not in taken:
            alternatives.append(candidate)
        if len(alternatives) >= _MAX_SUGGESTIONS:
            return alternatives

    dated = f"{stem}-{datetime.now(UTC).date().isoformat()}{suffix}"
    if dated.casefold() not in taken:
        alternatives.append(dated)
    return alternatives[:_MAX_SUGGESTIONS]


def suggested_folder_names(name: str, existing: Iterable[str]) -> list[str]:
    """Free alternatives for a clashing folder name (``auth``, ``auth-2``, …)."""
    taken = {item.casefold() for item in existing}
    alternatives: list[str] = []
    for attempt in range(2, _SUFFIX_ATTEMPTS + 1):
        candidate = f"{name}-{attempt}"
        if candidate.casefold() not in taken:
            alternatives.append(candidate)
        if len(alternatives) >= _MAX_SUGGESTIONS:
            break
    return alternatives
