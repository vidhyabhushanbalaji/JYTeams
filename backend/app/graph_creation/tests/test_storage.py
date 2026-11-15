"""Storage writes must survive a dropped connection, and duplicates stay a no-op."""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from app.core import retry
from app.graph_creation import storage


class _Bucket:
    """Replays scripted upload outcomes and counts the attempts."""

    def __init__(self, outcomes: list[object]) -> None:
        self._outcomes = list(outcomes)
        self.calls = 0
        self.keys: list[str] = []

    def upload(self, key: str, data: bytes, options: Any = None) -> object:
        self.calls += 1
        self.keys.append(key)
        outcome = self._outcomes.pop(0) if len(self._outcomes) > 1 else self._outcomes[0]
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


class _Client:
    """Minimal stand-in for the Supabase client (``client.storage.from_(bucket)``)."""

    def __init__(self, bucket: _Bucket) -> None:
        self.storage = _Storage(bucket)


class _Storage:
    def __init__(self, bucket: _Bucket) -> None:
        self._bucket = bucket

    def from_(self, name: str) -> _Bucket:
        return self._bucket


@pytest.fixture(autouse=True)
def _no_sleeping(monkeypatch: pytest.MonkeyPatch) -> None:
    """Retries must not make the suite wait."""
    monkeypatch.setattr(retry.time, "sleep", lambda _seconds: None)


def _store(
    monkeypatch: pytest.MonkeyPatch, outcomes: list[object]
) -> tuple[storage.SupabaseObjectStore, _Bucket]:
    bucket = _Bucket(outcomes)
    monkeypatch.setattr(storage, "admin_client", lambda: _Client(bucket))
    return storage.SupabaseObjectStore(bucket="project-files"), bucket


async def test_a_transient_socket_error_is_retried(monkeypatch: pytest.MonkeyPatch) -> None:
    store, bucket = _store(
        monkeypatch,
        [httpx.ReadError("[WinError 10035] non-blocking socket"), None],
    )

    stored = await store.put(project_id="p", digest="d", filename="guide.md", data=b"# G")

    assert stored.path == "p/d.md"
    assert stored.bucket == "project-files"
    assert bucket.calls == 2


async def test_a_repeated_failure_is_given_up_on_after_three_attempts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store, bucket = _store(monkeypatch, [httpx.ConnectError("connection reset")])

    with pytest.raises(storage.StorageError, match="could not store p/d.md"):
        await store.put(project_id="p", digest="d", filename="guide.md", data=b"# G")
    assert bucket.calls == 3


async def test_an_existing_object_is_not_an_error(monkeypatch: pytest.MonkeyPatch) -> None:
    store, bucket = _store(monkeypatch, [RuntimeError("The resource already exists")])

    stored = await store.put(project_id="p", digest="d", filename="guide.md", data=b"# G")

    assert stored.path == "p/d.md"
    # A duplicate is permanent, so it is never retried.
    assert bucket.calls == 1
