"""File storage for uploaded markdown, backed by Supabase Storage.

Objects are content-addressed (``{project_id}/{sha256}{suffix}``), so re-uploading the
same file costs one skipped write instead of a duplicate object, while the database still
keeps one row per uploaded path.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Protocol

from starlette.concurrency import run_in_threadpool

from app.core.retry import call_with_retries
from app.db.supabase import admin_client

logger = logging.getLogger(__name__)

_DUPLICATE_MARKERS = ("already exists", "duplicate", "resource already exists")


class StorageError(RuntimeError):
    """Uploading an object failed for a reason other than duplication."""


@dataclass(frozen=True)
class StoredObject:
    bucket: str
    path: str


def content_hash(data: bytes) -> str:
    """SHA-256 hex digest used for object keys and content de-duplication."""
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
                # A dropped connection must not fail a job whose folders are already described.
                call_with_retries(
                    lambda: (
                        admin_client()
                        .storage.from_(self.bucket)
                        .upload(key, data, {"content-type": "text/markdown"})
                    )
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
        """Read one stored object back (used when re-describing an existing folder)."""

        def download() -> bytes:
            try:
                return call_with_retries(
                    lambda: admin_client().storage.from_(bucket).download(path)
                )
            except Exception as exc:  # noqa: BLE001 - surfaced as one typed error
                raise StorageError(f"could not read {bucket}/{path}: {exc}") from exc

        return await run_in_threadpool(download)
