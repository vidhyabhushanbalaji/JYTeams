"""Shared pytest fixtures.

Tests are hermetic: the Supabase/Groq/Gemini settings are forced empty and auth runs in dev
mode, so the suite never reaches a real service even when a populated ``backend/.env``
exists.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app


@pytest.fixture(autouse=True)
def _isolate_settings(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Force a keyless, offline configuration for the duration of a test."""
    for name in (
        "SUPABASE_URL",
        "SUPABASE_ANON_KEY",
        "SUPABASE_SERVICE_ROLE_KEY",
        "GEMINI_API_KEY",
        "GROQ_API_KEY",
        "GROK_API_KEY",
        "CORS_ORIGINS",
    ):
        monkeypatch.setenv(name, "")
    monkeypatch.setenv("AUTH_MODE", "dev")
    monkeypatch.setenv("SUMMARIZER", "auto")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture()
def client() -> Iterator[TestClient]:
    """A TestClient with application lifespan (startup/shutdown) running."""
    with TestClient(create_app()) as test_client:
        yield test_client
