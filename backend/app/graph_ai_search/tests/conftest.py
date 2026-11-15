"""Section-local fixtures: hermetic settings, whatever ``backend/.env`` contains.

Conftest files only apply to their own subtree, so the section keeps its own copy of the
cross-cutting suite's isolation.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from app.core.config import get_settings


@pytest.fixture(autouse=True)
def _isolate_settings(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Force a keyless, offline configuration for every Graph AI Search test."""
    for name in (
        "SUPABASE_URL",
        "SUPABASE_ANON_KEY",
        "SUPABASE_SERVICE_ROLE_KEY",
        "GEMINI_API_KEY",
        "CORS_ORIGINS",
    ):
        monkeypatch.setenv(name, "")
    monkeypatch.setenv("AUTH_MODE", "dev")
    monkeypatch.setenv("DEV_USER_ID", "user-1")
    monkeypatch.setenv("SUMMARIZER", "gemini")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
