"""Read the incoming multipart upload into validated :class:`FileEntry` values.

Two shapes are accepted, both producing the same result:

* many files, where each part's ``filename`` carries the **relative path**
  (``docs/api/readme.md``) — what a ``webkitdirectory`` input or Electron sends;
* a single ``.zip`` archive, which is expanded in memory.

Zip entries are validated exactly like loose files, so archive traversal (``../``),
absolute paths and oversized entries are rejected either way.
"""

from __future__ import annotations

import io
import zipfile
from collections.abc import Sequence

from fastapi import UploadFile

from app.graph_creation.tree import FileEntry, UploadValidationError, normalise_path

_ENCRYPTED_FLAG = 0x1


async def collect_uploads(
    uploads: Sequence[UploadFile],
    *,
    max_files: int = 2000,
    max_file_bytes: int = 20 * 1024 * 1024,
    max_total_bytes: int = 200 * 1024 * 1024,
) -> list[FileEntry]:
    """Return the files of the request, enforcing the size and count limits."""
    if not uploads:
        raise UploadValidationError("no files were uploaded")

    first_name = (uploads[0].filename or "").lower()
    if len(uploads) == 1 and first_name.endswith(".zip"):
        archive_bytes = await uploads[0].read()
        if len(archive_bytes) > max_total_bytes:
            raise UploadValidationError(
                f"the archive is larger than the {max_total_bytes} byte limit"
            )
        return entries_from_zip(
            archive_bytes,
            max_files=max_files,
            max_file_bytes=max_file_bytes,
            max_total_bytes=max_total_bytes,
        )

    entries: list[FileEntry] = []
    total = 0
    for upload in uploads:
        path = normalise_path(upload.filename or "")
        data = await upload.read()
        if len(data) > max_file_bytes:
            raise UploadValidationError(
                f"{path!r}: larger than the {max_file_bytes} byte per-file limit"
            )
        total += len(data)
        if total > max_total_bytes:
            raise UploadValidationError(
                f"the upload is larger than the {max_total_bytes} byte limit"
            )
        entries.append(FileEntry(path=path, data=data))
        if len(entries) > max_files:
            raise UploadValidationError(f"the upload contains more than {max_files} files")
    return entries


def entries_from_zip(
    data: bytes,
    *,
    max_files: int,
    max_file_bytes: int,
    max_total_bytes: int,
) -> list[FileEntry]:
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise UploadValidationError("the uploaded .zip is not a valid archive") from exc

    entries: list[FileEntry] = []
    total = 0
    with archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            if info.flag_bits & _ENCRYPTED_FLAG:
                raise UploadValidationError("encrypted zip archives are not supported")
            if info.file_size > max_file_bytes:
                raise UploadValidationError(
                    f"{info.filename!r}: larger than the {max_file_bytes} byte per-file limit"
                )
            total += info.file_size
            if total > max_total_bytes:
                raise UploadValidationError(
                    f"the archive expands beyond the {max_total_bytes} byte limit"
                )
            entries.append(FileEntry(path=normalise_path(info.filename), data=archive.read(info)))
            if len(entries) > max_files:
                raise UploadValidationError(f"the upload contains more than {max_files} files")

    if not entries:
        raise UploadValidationError("the archive contains no files")
    return entries
