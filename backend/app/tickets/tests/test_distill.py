"""The distiller: ticket wording in, a short search query out (no network)."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

import pytest

from app.core.config import Settings
from app.tickets.distill import (
    CONTEXT_MAX_CHARS,
    DISTILL_PROMPT,
    MAX_POINTS,
    MAX_QUERY_CHARS,
    POINT_MAX_CHARS,
    GeminiDistiller,
    LocalDistiller,
    SearchTerms,
    build_distiller,
    context_from,
    searchable,
    terms_from_reply,
)

TICKET = "Review whether decision rights are still accurate"
DESCRIPTION = "Check the decision rights page against the current organisation chart."


class _Response:
    """Minimal stand-in for a ``GenerateContentResponse``."""

    def __init__(self, text: str | None) -> None:
        self.text = text


class _ScriptedModels:
    """Replays one scripted outcome per call and records how it was called."""

    def __init__(self, outcomes: list[object]) -> None:
        self._outcomes = list(outcomes)
        self.calls: list[dict[str, Any]] = []

    async def generate_content(self, *, model: str, contents: str, config: Any) -> Any:
        self.calls.append({"model": model, "prompt": contents, "config": config})
        outcome = self._outcomes.pop(0) if len(self._outcomes) > 1 else self._outcomes[0]
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


def _distiller(models: _ScriptedModels, *, model: str = "gemini-3.1-flash-lite") -> GeminiDistiller:
    """A Gemini distiller wired to a scripted fake client."""
    client = SimpleNamespace(aio=SimpleNamespace(models=models))
    return GeminiDistiller(api_key="", model=model, client=client)


async def test_the_offline_distiller_reduces_a_question_to_its_subject() -> None:
    terms = await LocalDistiller().terms(title=TICKET, description=DESCRIPTION)

    assert "decision" in terms.query
    assert "rights" in terms.query
    for noise in ("whether", "review", "still"):
        assert noise not in terms.query
    assert terms.points == ()
    assert len(terms.query.split()) <= 6


async def test_the_offline_distiller_says_so_when_there_is_nothing_to_search() -> None:
    with pytest.raises(ValueError):
        await LocalDistiller().terms(title="Review it", description="check this")


def test_a_fenced_reply_with_prose_around_it_is_understood() -> None:
    reply = (
        "Sure, here it is:\n```json\n"
        '{"query": "decision rights accurate", "terms": ["decision rights", "approval authority"]}'
        "\n```\n"
    )

    terms = terms_from_reply(reply)

    assert terms.query == "decision rights accurate"
    assert terms.points == ("decision rights", "approval authority")


def test_the_query_and_points_are_capped_and_deduplicated() -> None:
    reply = json.dumps(
        {
            "query": "x" * 300,
            "terms": ["a" * 100, "same", "SAME", "b", "c", "d", "e", "f"],
        }
    )

    terms = terms_from_reply(reply)

    assert len(terms.query) == MAX_QUERY_CHARS
    assert len(terms.points) == MAX_POINTS
    assert terms.points[1] == "same"
    assert all(len(point) <= POINT_MAX_CHARS for point in terms.points)


def test_a_reply_without_a_usable_query_is_rejected() -> None:
    with pytest.raises(ValueError):
        terms_from_reply('{"query": "", "terms": ["auth"]}')
    with pytest.raises(ValueError):
        terms_from_reply("I could not do that.")


def test_the_prompt_carries_the_reduction_that_matters() -> None:
    prompt = DISTILL_PROMPT.format(title=TICKET, description=DESCRIPTION)

    assert "decision rights accurate" in prompt
    assert TICKET in prompt


def test_the_context_is_the_points_joined_and_clipped() -> None:
    terms = SearchTerms(query="auth", points=("tokens rotate hourly", "session cookies"))

    assert context_from(terms) == "tokens rotate hourly · session cookies"
    long = SearchTerms(query="auth", points=tuple(["point " * 10] * MAX_POINTS))
    assert len(context_from(long)) <= CONTEXT_MAX_CHARS


def test_a_query_shorter_than_the_search_accepts_is_not_searchable() -> None:
    assert not searchable(SearchTerms(query="ab"))
    assert searchable(SearchTerms(query="abc"))


async def test_the_gemini_distiller_asks_for_json_at_zero_temperature() -> None:
    models = _ScriptedModels([_Response('{"query": "decision rights", "terms": ["approval"]}')])

    terms = await _distiller(models).terms(title=TICKET, description=DESCRIPTION)

    assert terms.query == "decision rights"
    assert terms.points == ("approval",)
    assert terms.model == "gemini-3.1-flash-lite"
    config = models.calls[0]["config"]
    assert config.temperature == 0
    assert config.response_mime_type == "application/json"
    assert TICKET in models.calls[0]["prompt"]


async def test_an_empty_reply_is_reported_and_never_returned() -> None:
    models = _ScriptedModels([_Response(None)])

    with pytest.raises(RuntimeError, match="empty"):
        await _distiller(models).terms(title=TICKET, description="")


async def test_a_rejected_key_fails_on_the_first_call() -> None:
    models = _ScriptedModels([RuntimeError("API key not valid")])

    with pytest.raises(RuntimeError):
        await _distiller(models).terms(title=TICKET, description="")
    assert len(models.calls) == 1


def test_without_a_key_the_offline_distiller_is_used() -> None:
    settings = Settings(gemini_api_key="", summarizer="gemini")

    assert isinstance(build_distiller(settings), LocalDistiller)


def test_a_mock_summarizer_never_reaches_a_model() -> None:
    settings = Settings(gemini_api_key="a-real-looking-key", summarizer="mock")

    assert isinstance(build_distiller(settings), LocalDistiller)


def test_with_a_key_the_gemini_distiller_is_used() -> None:
    settings = Settings(gemini_api_key="test-key", gemini_model="gemini-3.1-flash-lite")

    distiller = build_distiller(settings)

    assert isinstance(distiller, GeminiDistiller)
    assert distiller.model_name == "gemini-3.1-flash-lite"
