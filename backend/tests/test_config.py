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


def test_auto_prefers_groq_when_its_key_is_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
    get_settings.cache_clear()

    assert Settings().resolved_summarizer == "groq"


def test_the_grok_spelling_is_accepted_as_an_alias(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setenv("GROK_API_KEY", "gsk_mistyped")
    get_settings.cache_clear()

    assert Settings().groq_api_key == "gsk_mistyped"


def test_an_explicit_summarizer_wins_over_auto(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-test")
    monkeypatch.setenv("SUMMARIZER", "gemini")
    get_settings.cache_clear()

    assert Settings().resolved_summarizer == "gemini"


def test_groq_models_keep_their_order_and_deduplicate() -> None:
    settings = Settings(groq_model="a", groq_fallback_models=" b , a ,, c ")

    assert settings.groq_models == ("a", "b", "c")


def test_gemini_fallbacks_start_with_the_lite_models() -> None:
    settings = Settings()

    assert settings.gemini_models[0] == settings.gemini_model
    assert settings.gemini_models[1].endswith("-flash-lite")


def test_summary_concurrency_is_bounded() -> None:
    from pydantic import ValidationError

    assert Settings().summary_concurrency == 4
    with pytest.raises(ValidationError):
        Settings(summary_concurrency=0)


def test_description_and_pacing_defaults() -> None:
    settings = Settings()

    assert settings.description_max_chars == 300
    assert settings.llm_min_interval_seconds == 2.0


def test_description_max_chars_is_bounded() -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        Settings(description_max_chars=10)
