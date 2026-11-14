"""Turn an upload into a validated directory tree.

A *leaf* is not a separate type: it is simply a directory with no child directories.
Empty directories are dropped, because the graph only stores directories that lead to at
least one file. Children are ordered deterministically so that descriptions are stable for
the same input.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field

_MAX_PATH_LENGTH = 1024
_MAX_LABEL_LENGTH = 80


class UploadValidationError(ValueError):
    """The upload cannot be turned into a valid tree."""


@dataclass(frozen=True)
class FileEntry:
    """One uploaded file: normalised posix path plus its bytes."""

    path: str
    data: bytes

    @property
    def name(self) -> str:
        return self.path.rsplit("/", 1)[-1]

    @property
    def size(self) -> int:
        return len(self.data)


@dataclass
class DirectoryNode:
    """One directory in the tree. The root has an empty name and path."""

    name: str
    path: str
    depth: int
    ltree_path: str = ""
    files: list[FileEntry] = field(default_factory=list)
    directories: list[DirectoryNode] = field(default_factory=list)
    parent: DirectoryNode | None = field(default=None, repr=False, compare=False)

    @property
    def is_leaf(self) -> bool:
        """A leaf has files but no child directories."""
        return not self.directories

    @property
    def direct_file_count(self) -> int:
        return len(self.files)

    @property
    def child_directory_count(self) -> int:
        return len(self.directories)

    @property
    def total_files(self) -> int:
        return len(self.files) + sum(child.total_files for child in self.directories)

    def ancestors(self) -> Iterator[DirectoryNode]:
        """Yield parents, nearest first."""
        node = self.parent
        while node is not None:
            yield node
            node = node.parent


def normalise_path(raw: str) -> str:
    """Return a safe, normalised relative path or raise ``UploadValidationError``."""
    if not raw or not raw.strip():
        raise UploadValidationError("a file entry has an empty name")

    value = unicodedata.normalize("NFC", raw.replace("\\", "/").strip())
    if value.startswith("/") or re.match(r"^[A-Za-z]:", value):
        raise UploadValidationError(f"{raw!r}: absolute paths are not allowed")
    if len(value) > _MAX_PATH_LENGTH:
        raise UploadValidationError(f"{raw!r}: path is too long")

    parts = [part for part in value.split("/") if part not in ("", ".")]
    if not parts:
        raise UploadValidationError(f"{raw!r}: path is empty")
    for part in parts:
        if part == "..":
            raise UploadValidationError(f"{raw!r}: '..' is not allowed in upload paths")
        if "\x00" in part:
            raise UploadValidationError(f"{raw!r}: invalid character in path")
    return "/".join(parts)


def natural_key(value: str) -> tuple:
    """Case-insensitive, number-aware sort key (``file2`` before ``file10``)."""
    key: list[tuple[int, object]] = []
    for part in re.split(r"(\d+)", value):
        if not part:
            continue
        key.append((0, int(part)) if part.isdigit() else (1, part.casefold()))
    return tuple(key)


def build_tree(
    entries: Iterable[FileEntry],
    *,
    max_depth: int = 32,
    max_files: int = 2000,
) -> DirectoryNode:
    """Build, prune, sort and label the tree. Raises ``UploadValidationError``."""
    root = DirectoryNode(name="", path="", depth=0)
    index: dict[str, DirectoryNode] = {"": root}
    seen_paths: set[str] = set()

    for entry in entries:
        if len(seen_paths) >= max_files:
            raise UploadValidationError(f"the upload contains more than {max_files} files")
        if entry.path in seen_paths:
            raise UploadValidationError(f"duplicate path in upload: {entry.path!r}")
        seen_paths.add(entry.path)

        segments = entry.path.split("/")
        if len(segments) - 1 > max_depth:
            raise UploadValidationError(f"{entry.path!r}: deeper than the {max_depth} level limit")

        node = root
        for depth, segment in enumerate(segments[:-1], start=1):
            child_path = "/".join(segments[:depth])
            child = index.get(child_path)
            if child is None:
                child = DirectoryNode(name=segment, path=child_path, depth=depth, parent=node)
                node.directories.append(child)
                index[child_path] = child
            node = child
        node.files.append(entry)

    if not seen_paths:
        raise UploadValidationError("the upload contains no files")

    _prune_empty(root)
    if not root.files and not root.directories:
        raise UploadValidationError("the upload contains no usable files")

    _sort_tree(root)
    _assign_ltree_paths(root)
    return root


def _prune_empty(node: DirectoryNode) -> None:
    """Drop directories that lead to no files (bottom-up)."""
    kept: list[DirectoryNode] = []
    for child in node.directories:
        _prune_empty(child)
        if child.files or child.directories:
            kept.append(child)
    node.directories = kept


def _sort_tree(node: DirectoryNode) -> None:
    node.directories.sort(key=lambda child: natural_key(child.name))
    node.files.sort(key=lambda entry: natural_key(entry.name))
    for child in node.directories:
        _sort_tree(child)


def ltree_label(name: str) -> str:
    """Map a directory name onto a legal ltree label (lowercase alphanumerics/underscore)."""
    ascii_name = (
        unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii").lower()
    )
    label = re.sub(r"[^a-z0-9_]+", "_", ascii_name).strip("_")
    return (label or "x")[:_MAX_LABEL_LENGTH]


def _assign_ltree_paths(node: DirectoryNode) -> None:
    """Give every directory a unique ltree path (suffixing sibling label collisions)."""
    used: set[str] = set()
    for child in node.directories:
        base = ltree_label(child.name)
        label = base
        suffix = 1
        while label in used:
            label = f"{base}_{suffix}"
            suffix += 1
        used.add(label)
        child.ltree_path = f"{node.ltree_path}.{label}" if node.ltree_path else label
        _assign_ltree_paths(child)


def postorder(root: DirectoryNode) -> Iterator[DirectoryNode]:
    """Children before parents — the order descriptions must be produced in."""
    for child in root.directories:
        yield from postorder(child)
    yield root


def by_depth(root: DirectoryNode) -> Iterator[list[DirectoryNode]]:
    """One level at a time, root first — the order rows must be inserted in."""
    level = [root]
    while level:
        yield level
        level = [child for node in level for child in node.directories]


def find(root: DirectoryNode, path: str) -> DirectoryNode | None:
    """Locate a directory by its path (``""`` is the root)."""
    if path == "":
        return root
    node = root
    for segment in path.split("/"):
        node = next((child for child in node.directories if child.name == segment), None)
        if node is None:
            return None
    return node
