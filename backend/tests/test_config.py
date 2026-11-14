"""Settings parsing: defaults, env handling and the CORS list format."""

from __future__ import annotations

import pytest

from app.core.config import Settings, get_settings


def test_settings_have_safe_defaults() -> None:
    settings = get_settings()

    assert settings.api_prefix == "/api"
    assert settings.auth_mode == "dev"
    assert settings.supabase_configured is False
    assert settings.resolved_summarizer == "mock"


def test_cors_origins_accept_a_comma_separated_env_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "http://a.test, http://b.test")
    get_settings.cache_clear()

    assert Settings().cors_origins == ["http://a.test", "http://b.test"]


def test_cors_origins_accept_a_json_list(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", '["http://c.test"]')
    get_settings.cache_clear()

    assert Settings().cors_origins == ["http://c.test"]


def test_services_count_as_configured_only_with_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-role")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    get_settings.cache_clear()

    settings = Settings()

    assert settings.supabase_configured is True
    assert settings.resolved_summarizer == "gemini"


def test_leaving_supabase_url_unset_means_unconfigured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-role")
    get_settings.cache_clear()

    assert Settings().supabase_configured is False
