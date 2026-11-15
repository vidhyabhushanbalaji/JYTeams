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


def test_a_leftover_groq_key_selects_no_describer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Groq is retired: an old key in .env must not bring a describer back."""
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
    get_settings.cache_clear()

    assert Settings().resolved_summarizer == "mock"


def test_gemini_wins_when_a_groq_key_is_also_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-test")
    get_settings.cache_clear()

    assert Settings().resolved_summarizer == "gemini"


def test_an_explicit_mock_summarizer_wins_over_a_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-test")
    monkeypatch.setenv("SUMMARIZER", "mock")
    get_settings.cache_clear()

    assert Settings().resolved_summarizer == "mock"


def test_the_shipped_default_model_is_gemini_3_1_flash_lite() -> None:
    assert Settings.model_fields["gemini_model"].default == "gemini-3.1-flash-lite"
    # No fallbacks by default: every description is written by the configured model.
    assert Settings.model_fields["gemini_fallback_models"].default == ""


def test_thinking_is_off_unless_a_level_is_configured() -> None:
    assert Settings.model_fields["gemini_thinking_level"].default == ""
    assert Settings().gemini_thinking_level == ""
    # ``thinking_level`` replaces the numeric budget, which models from 3.5 reject.
    assert "gemini_thinking_budget" not in Settings.model_fields


def test_a_thinking_level_is_normalised_and_validated() -> None:
    from pydantic import ValidationError

    assert Settings(gemini_thinking_level=" HIGH ").gemini_thinking_level == "high"
    with pytest.raises(ValidationError):
        Settings(gemini_thinking_level="turbo")


def test_gemini_models_keep_their_order_and_deduplicate() -> None:
    settings = Settings(gemini_model="a", gemini_fallback_models=" b , a ,, c ")

    assert settings.gemini_models == ("a", "b", "c")


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
