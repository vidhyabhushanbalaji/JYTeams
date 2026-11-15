"""Minimal Groq client (OpenAI-compatible chat completions) shared by the describers.

``httpx`` is already a runtime dependency, so no SDK is added. The client owns the parts a
describer should not: model fallback, rate-limit backoff, and turning provider failures into
errors a person can act on.

Groq reports its limits in response headers: a ``429`` carries ``retry-after`` (seconds) and
``x-ratelimit-remaining-requests`` (daily requests left). A per-model daily exhaustion moves
to the next model immediately instead of sleeping until tomorrow.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass

import httpx

from app.core.pacing import RequestPacer

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://api.groq.com/openai/v1"
MAX_ATTEMPTS = 3
DEFAULT_TIMEOUT_SECONDS = 30.0
_MAX_RETRY_AFTER_SECONDS = 15.0


class GroqError(RuntimeError):
    """A Groq call could not produce text with any configured model."""


class GroqAuthError(GroqError):
    """The API key was rejected; no retry or fallback model can help."""


@dataclass(frozen=True)
class Completion:
    """One answer, with the model that actually produced it."""

    text: str
    model: str


class _Retryable(Exception):
    """The same model is worth trying again after a short delay."""

    def __init__(self, message: str, delay: float) -> None:
        super().__init__(message)
        self.delay = delay


class _NextModel(Exception):
    """This model cannot answer now; move on to the next one."""


class GroqClient:
    """One chat-completions call, retried across models until one answers."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        fallback_models: Sequence[str] = (),
        base_url: str = DEFAULT_BASE_URL,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        min_interval_seconds: float = 0.0,
        transport: httpx.AsyncBaseTransport | None = None,
        sleep: Callable[[float], Awaitable[None]] | None = None,
        pacer: RequestPacer | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("GROQ_API_KEY is required for the Groq describer")
        names = [model, *fallback_models]
        self._models = tuple(dict.fromkeys(name.strip() for name in names if name and name.strip()))
        self._model = model
        self._sleep = sleep or asyncio.sleep
        self._pacer = pacer or RequestPacer(min_interval_seconds)
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/") + "/",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout_seconds,
            transport=transport,
        )

    @property
    def model_name(self) -> str:
        """The configured primary model (the fallbacks only answer when it cannot)."""
        return self._model

    @property
    def models(self) -> tuple[str, ...]:
        return self._models

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> GroqClient:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()

    async def complete(
        self,
        prompt: str,
        *,
        max_tokens: int = 1024,
        json_mode: bool = False,
    ) -> Completion:
        """Return the first non-empty answer, trying each configured model in turn."""
        failures: list[str] = []
        for model in self._models:
            for attempt in range(1, MAX_ATTEMPTS + 1):
                try:
                    return await self._call(
                        model=model, prompt=prompt, max_tokens=max_tokens, json_mode=json_mode
                    )
                except GroqAuthError:
                    raise
                except _NextModel as exc:
                    failures.append(f"{model}: {exc}")
                    break
                except _Retryable as exc:
                    failures.append(f"{model}: {exc}")
                    if attempt < MAX_ATTEMPTS:
                        await self._sleep(exc.delay)
                        continue
                    break
                except httpx.HTTPError as exc:
                    failures.append(f"{model}: {type(exc).__name__}: {exc}")
                    if attempt < MAX_ATTEMPTS:
                        await self._sleep(float(attempt))
                        continue
                    break
                except Exception as exc:  # noqa: BLE001 - surfaced to the caller below
                    failures.append(f"{model}: {type(exc).__name__}: {str(exc)[:200]}")
                    break

        detail = "; ".join(failures[-6:])
        raise GroqError(f"Groq failed for every model: {detail}")

    async def _call(
        self, *, model: str, prompt: str, max_tokens: int, json_mode: bool
    ) -> Completion:
        waited = await self._pacer.wait()
        if waited:
            logger.debug("Paced %.2fs before calling %s", waited, model)
        body: dict[str, object] = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
            "max_tokens": max_tokens,
        }
        if json_mode:
            body["response_format"] = {"type": "json_object"}

        started = time.perf_counter()
        response = await self._client.post("chat/completions", json=body)
        elapsed_ms = int((time.perf_counter() - started) * 1000)

        if response.status_code == 400 and json_mode and "response_format" in response.text.lower():
            logger.info("Model %s rejected response_format; retrying without it", model)
            return await self._call(
                model=model, prompt=prompt, max_tokens=max_tokens, json_mode=False
            )
        if response.status_code in (401, 403):
            raise GroqAuthError(
                f"Groq rejected the API key (HTTP {response.status_code}); "
                f"check GROQ_API_KEY. {response.text[:200]}"
            )
        if response.status_code == 404:
            raise _NextModel("model not found")
        if response.status_code == 429:
            if response.headers.get("x-ratelimit-remaining-requests") == "0":
                raise _NextModel("daily request limit reached")
            raise _Retryable("rate limited", _retry_after(response))
        if response.status_code >= 500:
            raise _Retryable(f"HTTP {response.status_code}", 1.5)
        if response.status_code >= 400:
            raise _NextModel(f"HTTP {response.status_code}: {response.text[:200]}")

        payload = response.json()
        choices = payload.get("choices") if isinstance(payload, dict) else None
        content = ""
        if isinstance(choices, list) and choices:
            message = choices[0].get("message") if isinstance(choices[0], dict) else None
            if isinstance(message, dict) and isinstance(message.get("content"), str):
                content = message["content"]
        if not content.strip():
            raise _NextModel("empty response")

        usage = payload.get("usage") if isinstance(payload, dict) else None
        tokens = usage if isinstance(usage, dict) else {}
        logger.info(
            "Groq %s answered in %d ms (%s prompt / %s completion tokens)",
            model,
            elapsed_ms,
            tokens.get("prompt_tokens", "?"),
            tokens.get("completion_tokens", "?"),
        )
        return Completion(text=content.strip(), model=model)


def _retry_after(response: httpx.Response) -> float:
    """Seconds to wait from a 429, clamped so one call cannot stall the whole job."""
    raw = response.headers.get("retry-after", "").strip()
    try:
        seconds = float(raw)
    except ValueError:
        seconds = 2.0
    return max(1.0, min(seconds, _MAX_RETRY_AFTER_SECONDS))
