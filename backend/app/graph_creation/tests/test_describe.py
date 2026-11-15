"""Behaviour of the Gemini describer against a stubbed client (no network)."""

from __future__ import annotations

from collections.abc import Sequence
from types import SimpleNamespace
from typing import Any

import pytest

from app.graph_creation import describe
from app.graph_creation.describe import (
    GeminiDescriber,
    MockDescriber,
    trim_for_prompt,
)


class _Response:
    """Minimal stand-in for a ``GenerateContentResponse``."""

    def __init__(self, text: str | None) -> None:
        self.text = text
        self.candidates: list[Any] = []


class _ScriptedModels:
    """Replays one scripted outcome per model and records how it was called."""

    def __init__(self, outcomes: dict[str, list[object]]) -> None:
        self._outcomes = {model: list(items) for model, items in outcomes.items()}
        self.calls: list[tuple[str, bool]] = []
        self.prompts: list[str] = []

    async def generate_content(self, *, model: str, contents: str, config: Any) -> Any:
        include_thinking = getattr(config, "thinking_config", None) is not None
        self.calls.append((model, include_thinking))
        self.prompts.append(contents)
        queue = self._outcomes.get(model)
        if not queue:
            raise AssertionError(f"unexpected call to {model}")
        outcome = queue.pop(0) if len(queue) > 1 else queue[0]
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


def _describer(
    models: _ScriptedModels,
    *,
    model: str = "gemini-2.5-flash-lite",
    thinking_level: str = "",
    max_output_tokens: int = 1024,
    fallback_models: Sequence[str] | None = None,
) -> GeminiDescriber:
    """Build a describer wired to a scripted fake client."""
    client = SimpleNamespace(aio=SimpleNamespace(models=models))
    return GeminiDescriber(
        api_key="",
        model=model,
        max_output_tokens=max_output_tokens,
        thinking_level=thinking_level,
        fallback_models=fallback_models,
        client=client,
    )


async def _describe(describer: GeminiDescriber, name: str = "a.md", text: str = "# A") -> str:
    """Describe one folder, so the retry tests exercise the real prompt path."""
    result = await describer.describe_directory(path="folder", files=[(name, text)], directories=[])
    return result.text


def test_requires_an_api_key_when_building_its_own_client() -> None:
    with pytest.raises(ValueError):
        GeminiDescriber(api_key="", model="gemini-2.5-flash-lite")


async def test_a_blank_thinking_level_sends_no_thinking_config() -> None:
    models = _ScriptedModels({"m": [_Response("A guide.")]})
    describer = _describer(models, model="m", thinking_level="")

    assert await _describe(describer) == "A guide."
    assert models.calls == [("m", False)]


async def test_a_configured_thinking_level_is_sent() -> None:
    models = _ScriptedModels({"m": [_Response("A guide.")]})
    describer = _describer(models, model="m", thinking_level="high")

    await _describe(describer)
    assert models.calls == [("m", True)]


async def test_rejected_thinking_config_is_retried_without_it() -> None:
    rejected = RuntimeError("400 INVALID_ARGUMENT. Request contains an invalid argument.")
    models = _ScriptedModels({"m": [rejected, _Response("A guide.")]})
    describer = _describer(models, model="m", thinking_level="high")

    assert await _describe(describer) == "A guide."
    assert models.calls == [("m", True), ("m", False)]


async def test_thinking_is_dropped_for_later_calls_once_rejected() -> None:
    rejected = RuntimeError("400 INVALID_ARGUMENT. Request contains an invalid argument.")
    models = _ScriptedModels({"m": [rejected, _Response("A guide."), _Response("Another.")]})
    describer = _describer(models, model="m", thinking_level="high")

    await _describe(describer, "a.md", "# A")
    await _describe(describer, "b.md", "# B")

    assert models.calls == [("m", True), ("m", False), ("m", False)]


async def test_quota_errors_skip_to_the_next_model_without_retrying() -> None:
    quota = RuntimeError(
        "429 RESOURCE_EXHAUSTED. You exceeded your current quota, please check your plan."
    )
    models = _ScriptedModels({"m": [quota], "gemini-2.5-flash": [_Response("Fallback.")]})
    describer = _describer(
        models, model="m", thinking_level="", fallback_models=("gemini-2.5-flash",)
    )

    assert await _describe(describer) == "Fallback."
    assert [model for model, _ in models.calls] == ["m", "gemini-2.5-flash"]


async def test_overload_is_retried_on_the_same_model(monkeypatch: pytest.MonkeyPatch) -> None:
    sleeps: list[float] = []

    async def fake_sleep(delay: float) -> None:
        sleeps.append(delay)

    monkeypatch.setattr(describe.asyncio, "sleep", fake_sleep)

    overload = RuntimeError("503 UNAVAILABLE: the model is overloaded")
    models = _ScriptedModels({"m": [overload, overload, _Response("Third time lucky.")]})
    describer = _describer(models, model="m", thinking_level="")

    assert await _describe(describer) == "Third time lucky."
    assert sleeps == [1.0, 2.0]


async def test_empty_text_with_thinking_retries_without_it() -> None:
    models = _ScriptedModels({"m": [_Response(""), _Response("A guide.")]})
    describer = _describer(models, model="m", thinking_level="high")

    assert await _describe(describer) == "A guide."
    assert models.calls == [("m", True), ("m", False)]


async def test_every_model_failing_reports_the_last_error() -> None:
    failure = RuntimeError("400 INVALID_ARGUMENT. Request contains an invalid argument.")
    models = _ScriptedModels(
        {
            "m": [failure],
            "gemini-2.5-flash": [failure],
            "gemini-2.5-pro": [failure],
        }
    )
    describer = _describer(
        models,
        model="m",
        thinking_level="",
        fallback_models=("gemini-2.5-flash", "gemini-2.5-pro"),
    )

    with pytest.raises(RuntimeError, match="failed for every model"):
        await _describe(describer)
    assert len(models.calls) == 3


async def test_without_fallbacks_only_the_configured_model_is_called() -> None:
    """The default chain is empty, so a failure surfaces instead of another model answering."""
    failure = RuntimeError("429 RESOURCE_EXHAUSTED. You exceeded your current quota.")
    models = _ScriptedModels({"gemini-2.5-flash-lite": [failure]})
    describer = _describer(models)

    with pytest.raises(RuntimeError, match="failed for every model"):
        await _describe(describer)
    assert models.calls == [("gemini-2.5-flash-lite", False)]


async def test_bad_api_key_fails_immediately() -> None:
    models = _ScriptedModels({"m": [RuntimeError("401 UNAUTHENTICATED: API key not valid")]})
    describer = _describer(models, model="m", thinking_level="")

    with pytest.raises(RuntimeError, match="API key not valid"):
        await _describe(describer)
    assert len(models.calls) == 1


async def test_the_prompt_carries_the_file_text_and_the_child_descriptions() -> None:
    models = _ScriptedModels({"m": [_Response("Described.")]})
    describer = _describer(models, model="m")

    await describer.describe_directory(
        path="guides",
        files=[("deployment.md", "# Deployment\n\nRoll back with Helm.")],
        directories=[("rollback", "Reverting a bad release.")],
    )

    prompt = models.prompts[0]
    assert "Folder: guides" in prompt
    assert "### deployment.md" in prompt
    assert "Roll back with Helm." in prompt
    assert "- rollback: Reverting a bad release." in prompt
    assert "at most 300 characters" in prompt


async def test_the_prompt_asks_for_plain_prose_without_compound_identifiers() -> None:
    models = _ScriptedModels({"m": [_Response("Described.")]})
    describer = _describer(models, model="m")

    await describer.describe_directory(
        path="operations",
        files=[("rollback-runbook.md", "# Rollback runbook\n\nRevert a release.")],
        directories=[],
    )

    prompt = models.prompts[0]
    assert "never use hyphens, underscores or run-together identifiers" in prompt
    assert "'rollback plan', not 'rollback-plan'" in prompt


def test_trim_for_prompt_caps_each_file_and_the_folder_total() -> None:
    files = [("a.md", "x" * 5000), ("b.md", "y" * 5000)]

    trimmed = trim_for_prompt(files, per_file=1_500, total=2_000)

    # 2000 / 2 files = 1000 characters each, which is tighter than the per-file cap; the
    # truncation marker is appended on top.
    assert [text[:1000] for _, text in trimmed] == ["x" * 1000, "y" * 1000]
    assert all(text.endswith("[… truncated …]") for _, text in trimmed)
    assert all(len(text) == 1016 for _, text in trimmed)


def test_trim_for_prompt_keeps_short_files_untouched() -> None:
    files = [("a.md", "# A"), ("b.md", "# B")]

    assert trim_for_prompt(files, per_file=1_500, total=24_000) == files


async def test_the_mock_describer_names_the_files_and_their_headings() -> None:
    result = await MockDescriber().describe_directory(
        path="docs",
        files=[("alpha.md", "# Alpha\n\nbody"), ("beta.md", "# Beta")],
        directories=[("api", "Endpoints.")],
    )

    description = result.text
    assert result.model == "mock"
    assert "docs holds 2 file(s) and 1 subfolder(s)." in description
    assert "Alpha" in description and "Beta" in description
    assert "Subfolders: api." in description
