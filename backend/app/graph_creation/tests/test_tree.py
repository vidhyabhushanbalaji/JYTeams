"""Tree building: path safety, pruning, ordering and the ltree projection."""

from __future__ import annotations

import pytest

from app.graph_creation.tree import (
    FileEntry,
    UploadValidationError,
    build_tree,
    by_depth,
    ltree_label,
    natural_key,
    normalise_path,
    postorder,
)


def test_normalise_path_rejects_absolute_and_traversal() -> None:
    with pytest.raises(UploadValidationError):
        normalise_path("/etc/passwd")
    with pytest.raises(UploadValidationError):
        normalise_path("C:\\Windows\\win.ini")
    with pytest.raises(UploadValidationError):
        normalise_path("docs/../../secrets.md")
    with pytest.raises(UploadValidationError):
        normalise_path("   ")


def test_normalise_path_folds_separators_and_dot_segments() -> None:
    assert normalise_path("docs\\api\\./readme.md") == "docs/api/readme.md"


def test_children_are_sorted_naturally() -> None:
    tree = build_tree(
        [
            FileEntry("file10.md", b"x"),
            FileEntry("file2.md", b"x"),
            FileEntry("File1.md", b"x"),
        ]
    )

    assert [entry.name for entry in tree.files] == ["File1.md", "file2.md", "file10.md"]
    assert natural_key("a1") < natural_key("a2") < natural_key("a10")


def test_tree_creates_only_directories_that_lead_to_files() -> None:
    tree = build_tree(
        [
            FileEntry("README.md", b"x"),
            FileEntry("docs/api/auth.md", b"x"),
        ]
    )

    assert [child.path for child in tree.directories] == ["docs"]
    assert [child.path for child in tree.directories[0].directories] == ["docs/api"]
    assert tree.total_files == 2
    assert tree.directories[0].directories[0].is_leaf is True


def test_postorder_visits_children_before_parents() -> None:
    tree = build_tree([FileEntry("a/b/c/file.md", b"x")])

    assert [node.path for node in postorder(tree)] == ["a/b/c", "a/b", "a", ""]
    assert [[node.path for node in level] for level in by_depth(tree)] == [
        [""],
        ["a"],
        ["a/b"],
        ["a/b/c"],
    ]


def test_ltree_labels_are_sanitised_and_unique_per_parent() -> None:
    tree = build_tree(
        [
            FileEntry("My Docs/a.md", b"x"),
            FileEntry("my_docs/a.md", b"x"),
            FileEntry("r\u00e9sum\u00e9/a.md", b"x"),
        ]
    )

    labels = [child.ltree_path for child in tree.directories]

    assert labels == ["my_docs", "my_docs_1", "resume"]
    assert ltree_label("Ärger & Söhne") == "arger_sohne"


def test_limits_and_invalid_input_are_rejected() -> None:
    with pytest.raises(UploadValidationError, match="no files"):
        build_tree([])
    with pytest.raises(UploadValidationError, match="duplicate"):
        build_tree([FileEntry("a.md", b"x"), FileEntry("a.md", b"y")])
    with pytest.raises(UploadValidationError, match="more than"):
        build_tree([FileEntry("a.md", b"x")], max_files=0)
    with pytest.raises(UploadValidationError, match="deeper"):
        build_tree([FileEntry("a/b/c.md", b"x")], max_depth=1)
