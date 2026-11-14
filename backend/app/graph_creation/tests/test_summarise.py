"""Behaviour of the Gemini summariser against a stubbed client (no network)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from app.graph_creation import summarise
from app.graph_creation.summarise import GeminiSummarizer


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

    async def generate_content(self, *, model: str, contents: str, config: Any) -> Any:
        include_thinking = getattr(config, "thinking_config", None) is not None
        self.calls.append((model, include_thinking))
        queue = self._outcomes.get(model)
        if not queue:
            raise AssertionError(f"unexpected call to {model}")
        outcome = queue.pop(0) if len(queue) > 1 else queue[0]
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


def _summarizer(
    models: _ScriptedModels,
    *,
    model: str = "gemini-3.5-flash-lite",
    thinking_budget: int | None = 0,
    max_output_tokens: int = 1024,
) -> GeminiSummarizer:
    """Build a summariser wired to a scripted fake client."""
    client = SimpleNamespace(aio=SimpleNamespace(models=models))
    return GeminiSummarizer(
        api_key="",
        model=model,
        max_output_tokens=max_output_tokens,
        thinking_budget=thinking_budget,
        client=client,
    )


def test_requires_an_api_key_when_building_its_own_client() -> None:
    with pytest.raises(ValueError):
        GeminiSummarizer(api_key="", model="gemini-3.5-flash-lite")


async def test_zero_thinking_budget_sends_no_thinking_config() -> None:
    models = _ScriptedModels({"m": [_Response("A guide.")]})
    summarizer = _summarizer(models, model="m", thinking_budget=0)

    assert await summarizer.summarise_file(name="a.md", text="# A") == "A guide."
    assert models.calls == [("m", False)]


async def test_positive_thinking_budget_is_sent() -> None:
    models = _ScriptedModels({"m": [_Response("A guide.")]})
    summarizer = _summarizer(models, model="m", thinking_budget=512)

    await summarizer.summarise_file(name="a.md", text="# A")
    assert models.calls == [("m", True)]


async def test_rejected_thinking_config_is_retried_without_it() -> None:
    rejected = RuntimeError("400 INVALID_ARGUMENT. Request contains an invalid argument.")
    models = _ScriptedModels({"m": [rejected, _Response("A guide.")]})
    summarizer = _summarizer(models, model="m", thinking_budget=512)

    assert await summarizer.summarise_file(name="a.md", text="# A") == "A guide."
    assert models.calls == [("m", True), ("m", False)]


async def test_thinking_is_dropped_for_later_calls_once_rejected() -> None:
    rejected = RuntimeError("400 INVALID_ARGUMENT. Request contains an invalid argument.")
    models = _ScriptedModels({"m": [rejected, _Response("A guide."), _Response("Another.")]})
    summarizer = _summarizer(models, model="m", thinking_budget=512)

    await summarizer.summarise_file(name="a.md", text="# A")
    await summarizer.summarise_file(name="b.md", text="# B")

    assert models.calls == [("m", True), ("m", False), ("m", False)]


async def test_quota_errors_skip_to_the_next_model_without_retrying() -> None:
    quota = RuntimeError(
        "429 RESOURCE_EXHAUSTED. You exceeded your current quota, please check your plan."
    )
    models = _ScriptedModels({"m": [quota], "gemini-3.7-flash": [_Response("Fallback.")]})
    summarizer = _summarizer(models, model="m", thinking_budget=0)

    assert await summarizer.summarise_file(name="a.md", text="# A") == "Fallback."
    assert [model for model, _ in models.calls] == ["m", "gemini-3.7-flash"]


async def test_overload_is_retried_on_the_same_model(monkeypatch: pytest.MonkeyPatch) -> None:
    sleeps: list[float] = []

    async def fake_sleep(delay: float) -> None:
        sleeps.append(delay)

    monkeypatch.setattr(summarise.asyncio, "sleep", fake_sleep)

    overload = RuntimeError("503 UNAVAILABLE: the model is overloaded")
    models = _ScriptedModels({"m": [overload, overload, _Response("Third time lucky.")]})
    summarizer = _summarizer(models, model="m", thinking_budget=0)

    assert await summarizer.summarise_file(name="a.md", text="# A") == "Third time lucky."
    assert sleeps == [1.0, 2.0]


async def test_empty_text_with_thinking_retries_without_it() -> None:
    models = _ScriptedModels({"m": [_Response(""), _Response("A guide.")]})
    summarizer = _summarizer(models, model="m", thinking_budget=512)

    assert await summarizer.summarise_file(name="a.md", text="# A") == "A guide."
    assert models.calls == [("m", True), ("m", False)]


async def test_every_model_failing_reports_the_last_error() -> None:
    failure = RuntimeError("400 INVALID_ARGUMENT. Request contains an invalid argument.")
    models = _ScriptedModels(
        {
            "m": [failure],
            "gemini-3.7-flash": [failure],
            "gemini-3.5-flash": [failure],
            "gemini-3.8-flash": [failure],
        }
    )
    summarizer = _summarizer(models, model="m", thinking_budget=0)

    with pytest.raises(RuntimeError, match="failed for every model"):
        await summarizer.summarise_file(name="a.md", text="# A")
    assert len(models.calls) == 4


async def test_bad_api_key_fails_immediately() -> None:
    models = _ScriptedModels({"m": [RuntimeError("401 UNAUTHENTICATED: API key not valid")]})
    summarizer = _summarizer(models, model="m", thinking_budget=0)

    with pytest.raises(RuntimeError, match="API key not valid"):
        await summarizer.summarise_file(name="a.md", text="# A")
    assert len(models.calls) == 1
