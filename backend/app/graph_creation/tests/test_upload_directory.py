"""Local input handling for the upload tool: directories and .zip archives."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from app.graph_creation.tools.upload_directory import load_upload


def _write(root: Path, name: str, text: str) -> None:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _zip(path: Path, payload: dict[str, str]) -> Path:
    with zipfile.ZipFile(path, "w") as archive:
        for name, text in payload.items():
            archive.writestr(name, text)
    return path


def test_directory_is_read_as_relative_posix_paths(tmp_path: Path) -> None:
    _write(tmp_path, "README.md", "# Root")
    _write(tmp_path / "docs", "a.md", "# A")
    _write(tmp_path / ".git", "config", "ignored")

    upload = load_upload(tmp_path)

    assert sorted(path for path, _ in upload.entries) == ["README.md", "docs/a.md"]
    assert upload.archive is None
    assert upload.archive_name is None


def test_zip_archive_is_read_and_kept_for_upload(tmp_path: Path) -> None:
    archive = _zip(
        tmp_path / "project.zip", {"test_docs/a.md": "# A", "test_docs/docs/b.md": "# B"}
    )

    upload = load_upload(archive)

    assert [path for path, _ in upload.entries] == ["test_docs/a.md", "test_docs/docs/b.md"]
    assert upload.archive == archive.read_bytes()
    assert upload.archive_name == "project.zip"


def test_directory_and_zip_yield_the_same_entries(tmp_path: Path) -> None:
    source = tmp_path / "src"
    _write(source, "a.md", "# A")
    _write(source / "docs", "b.md", "# B")
    archive = _zip(tmp_path / "src.zip", {"a.md": "# A", "docs/b.md": "# B"})

    assert load_upload(archive).entries == load_upload(source).entries


def test_broken_archive_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "broken.zip"
    path.write_bytes(b"not a zip")

    with pytest.raises(SystemExit, match="invalid archive"):
        load_upload(path)


def test_archive_without_files_is_rejected(tmp_path: Path) -> None:
    archive = _zip(tmp_path / "folders-only.zip", {"docs/": ""})

    with pytest.raises(SystemExit, match="invalid archive"):
        load_upload(archive)


def test_missing_path_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(SystemExit, match="not a directory or .zip archive"):
        load_upload(tmp_path / "nope.zip")
