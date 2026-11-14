"""Upload parsing: multipart paths, zip archives, zip-slip and limits."""

from __future__ import annotations

import io
import zipfile

import pytest
from fastapi import UploadFile

from app.graph_creation.ingest import collect_uploads
from app.graph_creation.tree import UploadValidationError


def _upload(data: bytes, filename: str) -> UploadFile:
    return UploadFile(file=io.BytesIO(data), filename=filename, size=len(data))


def _zip(payload: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, data in payload.items():
            archive.writestr(name, data)
        archive.writestr("empty-dir/", b"")
    return buffer.getvalue()


async def test_multipart_uploads_keep_their_relative_paths() -> None:
    entries = await collect_uploads(
        [_upload(b"# A", "docs/api/a.md"), _upload(b"# B", "README.md")]
    )

    assert [entry.path for entry in entries] == ["docs/api/a.md", "README.md"]


async def test_zip_archive_is_expanded_and_directory_entries_skipped() -> None:
    entries = await collect_uploads([_upload(_zip({"docs/a.md": b"# A"}), "project.zip")])

    assert [entry.path for entry in entries] == ["docs/a.md"]


async def test_zip_slip_is_rejected() -> None:
    with pytest.raises(UploadValidationError, match=r"'\.\.'"):
        await collect_uploads([_upload(_zip({"../escape.md": b"x"}), "project.zip")])


async def test_broken_archive_is_rejected() -> None:
    with pytest.raises(UploadValidationError, match="not a valid archive"):
        await collect_uploads([_upload(b"not a zip", "project.zip")])


async def test_limits_are_enforced() -> None:
    with pytest.raises(UploadValidationError, match="no files"):
        await collect_uploads([])
    with pytest.raises(UploadValidationError, match="per-file"):
        await collect_uploads([_upload(b"x" * 10, "a.md")], max_file_bytes=5)
    with pytest.raises(UploadValidationError, match="more than"):
        await collect_uploads([_upload(b"x", "a.md")], max_files=0)
