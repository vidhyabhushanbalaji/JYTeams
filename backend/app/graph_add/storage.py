"""Blob storage for the document being placed.

The object key follows Graph Creation's convention exactly — ``{project_id}/{sha256}{suffix}``
— so a document that already exists in the project is stored once no matter how many paths
point at it. The convention is mirrored rather than imported (sections do not share
internals); only the bucket is shared configuration.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Protocol

from starlette.concurrency import run_in_threadpool

from app.db.supabase import admin_client

logger = logging.getLogger(__name__)

_DUPLICATE_MARKERS = ("already exists", "duplicate", "resource already exists")
_CONTENT_TYPE = "text/markdown"


class StorageError(RuntimeError):
    """Uploading an object failed for a reason other than duplication."""


@dataclass(frozen=True)
class StoredObject:
    bucket: str
    path: str


def content_hash(data: bytes) -> str:
    """SHA-256 hex digest used for object keys and duplicate-content reporting."""
    return hashlib.sha256(data).hexdigest()


def object_key(*, project_id: str, digest: str, filename: str) -> str:
    suffix = PurePosixPath(filename).suffix.lower()
    return f"{project_id}/{digest}{suffix}"


class ObjectStore(Protocol):
    """What the service needs from blob storage."""

    bucket: str

    async def put(
        self, *, project_id: str, digest: str, filename: str, data: bytes
    ) -> StoredObject: ...

    async def get(self, *, bucket: str, path: str) -> bytes: ...


class SupabaseObjectStore:
    """Supabase Storage implementation."""

    def __init__(self, *, bucket: str) -> None:
        self.bucket = bucket

    async def put(
        self,
        *,
        project_id: str,
        digest: str,
        filename: str,
        data: bytes,
    ) -> StoredObject:
        key = object_key(project_id=project_id, digest=digest, filename=filename)

        def upload() -> None:
            try:
                admin_client().storage.from_(self.bucket).upload(
                    key, data, {"content-type": _CONTENT_TYPE}
                )
            except Exception as exc:  # noqa: BLE001 - duplicates are expected and fine
                message = str(exc).lower()
                if any(marker in message for marker in _DUPLICATE_MARKERS):
                    logger.debug("Object %s already stored", key)
                    return
                raise StorageError(f"could not store {key}: {exc}") from exc

        await run_in_threadpool(upload)
        return StoredObject(bucket=self.bucket, path=key)

    async def get(self, *, bucket: str, path: str) -> bytes:
        """Read one stored document back (the text a placement refreshes descriptions from)."""

        def download() -> bytes:
            try:
                return admin_client().storage.from_(bucket).download(path)
            except Exception as exc:  # noqa: BLE001 - surfaced as one typed error
                raise StorageError(f"could not read {bucket}/{path}: {exc}") from exc

        return await run_in_threadpool(download)
