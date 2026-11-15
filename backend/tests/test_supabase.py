"""The Supabase client is built without HTTP/2.

storage3 defaults to ``http2=True``, and httpcore's sync HTTP/2 read raises ``WinError 10035``
on Windows when Graph Creation uploads run concurrently — which failed a job that had already
paid for every description. ``build_http_client`` is the one place that decision is made.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest

import app.db.supabase as supabase
from app.core.config import get_settings


def test_the_shared_client_disables_http2(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def fake_client(**kwargs: Any) -> object:
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(supabase.httpx, "Client", fake_client)

    supabase.build_http_client()

    assert captured["http2"] is False
    # storage3 sets this on its own client; keep it so downloads still follow redirects.
    assert captured["follow_redirects"] is True
    assert isinstance(captured["timeout"], httpx.Timeout)
    assert isinstance(captured["limits"], httpx.Limits)


def test_the_client_is_handed_to_supabase_through_its_options(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sentinel = object()
    captured: dict[str, Any] = {}

    def fake_create(url: str, key: str, options: Any = None) -> str:
        captured.update(url=url, key=key, options=options)
        return "supabase-client"

    monkeypatch.setattr(supabase, "build_http_client", lambda: sentinel)
    monkeypatch.setattr(supabase, "create_client", fake_create)
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-role")
    get_settings.cache_clear()
    supabase._cached_client.cache_clear()

    try:
        assert supabase.admin_client() == "supabase-client"
    finally:
        supabase._cached_client.cache_clear()

    assert captured["url"] == "https://example.supabase.co"
    assert captured["options"].httpx_client is sentinel
