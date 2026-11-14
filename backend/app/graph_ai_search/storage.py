"""Read access to the stored markdown, so search can match against real content.

Search used to read per-file summaries held in Postgres; it now reads the documents themselves,
which means this section needs its own blob access (sections may not import each other's
internals). Two things keep that affordable:

* objects are content-addressed (``{project_id}/{sha256}{suffix}``), so the digest is a natural
  cache key — the same bytes uploaded at ten paths is read once;
* a bounded LRU sits in front of the bucket, and a per-document character cap keeps one huge
  file from dominating a search.
"""

from __future__ import annotations

import logging
from collections import OrderedDict
from typing import Protocol

from starlette.concurrency import run_in_threadpool

from app.db.supabase import admin_client

logger = logging.getLogger(__name__)

_TRUNCATION_MARKER = "\n\n[… truncated …]"


class StorageUnavailable(RuntimeError):
    """A document could not be read back from the bucket."""


class BlobStore(Protocol):
    """What the reader needs from blob storage."""

    async def get(self, *, bucket: str, path: str) -> bytes: ...


class SupabaseBlobStore:
    """Supabase Storage implementation (service-role client, read-only use)."""

    async def get(self, *, bucket: str, path: str) -> bytes:
        def download() -> bytes:
            try:
                return admin_client().storage.from_(bucket).download(path)
            except Exception as exc:  # noqa: BLE001 - surfaced as one typed error
                raise StorageUnavailable(f"could not read {bucket}/{path}: {exc}") from exc

        return await run_in_threadpool(download)


class BlobCache:
    """Small bounded LRU keyed by content digest, holding decoded document text."""

    def __init__(self, *, max_entries: int = 256) -> None:
        self._max_entries = max(1, max_entries)
        self._entries: OrderedDict[str, str] = OrderedDict()

    def __len__(self) -> int:
        return len(self._entries)

    def get(self, key: str) -> str | None:
        value = self._entries.get(key)
        if value is not None:
            self._entries.move_to_end(key)
        return value

    def put(self, key: str, value: str) -> None:
        if not key:
            return
        self._entries[key] = value
        self._entries.move_to_end(key)
        while len(self._entries) > self._max_entries:
            self._entries.popitem(last=False)


class DocumentTextReader:
    """Reads one document's text, through the cache, decoding defensively."""

    def __init__(
        self,
        *,
        store: BlobStore,
        cache: BlobCache | None = None,
        max_chars: int = 200_000,
    ) -> None:
        self._store = store
        self._cache = cache or BlobCache()
        self._max_chars = max(1, max_chars)

    async def read(self, *, bucket: str, path: str, digest: str = "") -> str:
        """Return the document's text, or raise :class:`StorageUnavailable`."""
        if digest:
            cached = self._cache.get(digest)
            if cached is not None:
                return cached

        data = await self._store.get(bucket=bucket, path=path)
        text = self._decode(data)
        if digest:
            self._cache.put(digest, text)
        return text

    def _decode(self, data: bytes) -> str:
        # utf-8-sig accepts plain UTF-8 and strips a BOM; search must not fail over odd bytes.
        text = data.decode("utf-8-sig", errors="replace").strip()
        if len(text) > self._max_chars:
            return text[: self._max_chars] + _TRUNCATION_MARKER
        return text


def build_reader(*, cache_entries: int, max_chars: int) -> DocumentTextReader:
    """Wire the reader the router hands to the service (bucket comes from each file row)."""
    return DocumentTextReader(
        store=SupabaseBlobStore(),
        cache=BlobCache(max_entries=cache_entries),
        max_chars=max_chars,
    )
