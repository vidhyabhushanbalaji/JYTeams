"""The Groq client against a mocked transport: retries, limits, fallbacks (no network)."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable

import httpx
import pytest

from app.core.groq import GroqAuthError, GroqClient, GroqError


def _answer(text: str = "A guide.") -> dict[str, object]:
    return {
        "choices": [{"message": {"content": text}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5},
    }


def _client(
    handler: Callable[[httpx.Request], httpx.Response],
    *,
    models: tuple[str, ...] = ("primary",),
    sleep: Callable[[float], Awaitable[None]] | None = None,
) -> GroqClient:
    return GroqClient(
        api_key="gsk_test",
        model=models[0],
        fallback_models=models[1:],
        transport=httpx.MockTransport(handler),
        sleep=sleep,
    )


async def test_an_answer_records_the_model_and_calls_the_completions_endpoint() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/openai/v1/chat/completions"
        assert request.headers["authorization"] == "Bearer gsk_test"
        body = json.loads(request.content)
        assert body["temperature"] == 0
        return httpx.Response(200, json=_answer("Deployment guide."))

    async with _client(handler) as client:
        completion = await client.complete("Describe guides.")

    assert completion.text == "Deployment guide."
    assert completion.model == "primary"


async def test_a_429_waits_retry_after_and_tries_the_same_model_again() -> None:
    sleeps: list[float] = []
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(429, headers={"retry-after": "2"}, text="rate limited")
        return httpx.Response(200, json=_answer())

    async def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    async with _client(handler, sleep=fake_sleep) as client:
        completion = await client.complete("x")

    assert sleeps == [2.0]
    assert completion.text == "A guide."


async def test_a_daily_limit_moves_to_the_next_model_without_sleeping() -> None:
    slept: list[float] = []
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        model = json.loads(request.content)["model"]
        seen.append(model)
        if model == "primary":
            return httpx.Response(
                429, headers={"x-ratelimit-remaining-requests": "0"}, text="daily"
            )
        return httpx.Response(200, json=_answer("Second model."))

    async def fake_sleep(seconds: float) -> None:
        slept.append(seconds)

    async with _client(handler, models=("primary", "backup"), sleep=fake_sleep) as client:
        completion = await client.complete("x")

    assert completion.model == "backup"
    assert seen == ["primary", "backup"]
    assert slept == []


async def test_a_rejected_key_is_fatal_and_names_the_variable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text="Invalid API Key")

    async with _client(handler) as client:
        with pytest.raises(GroqAuthError, match="GROQ_API_KEY"):
            await client.complete("x")


async def test_an_unknown_model_falls_through_and_empty_answers_are_reported() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        model = json.loads(request.content)["model"]
        if model == "primary":
            return httpx.Response(404, text="model not found")
        return httpx.Response(200, json={"choices": [{"message": {"content": "  "}}]})

    async with _client(handler, models=("primary", "backup")) as client:
        with pytest.raises(GroqError) as excinfo:
            await client.complete("x")

    message = str(excinfo.value)
    assert "Groq failed for every model" in message
    assert "primary: model not found" in message
    assert "backup: empty response" in message


async def test_response_format_is_dropped_when_a_model_rejects_it() -> None:
    bodies: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        bodies.append(body)
        if "response_format" in body:
            return httpx.Response(400, text="response_format is not supported")
        return httpx.Response(200, json=_answer('{"descriptions": []}'))

    async with _client(handler) as client:
        completion = await client.complete("x", json_mode=True)

    assert "response_format" in bodies[0]
    assert "response_format" not in bodies[1]
    assert completion.text == '{"descriptions": []}'


def test_a_key_is_required() -> None:
    with pytest.raises(ValueError):
        GroqClient(api_key="", model="openai/gpt-oss-120b")
