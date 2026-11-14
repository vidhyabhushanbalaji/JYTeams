"""Summarisation: one short summary per file, one description per directory.

Directories are described bottom-up: a directory's prompt is built from its child file
summaries and its child directory descriptions, so the root ends up describing the whole
project. Two implementations exist - ``GeminiSummarizer`` (real) and ``MockSummarizer``
(deterministic, no network) - selected by ``SUMMARIZER``/``GEMINI_API_KEY``.

Three provider quirks are handled here, because each of them used to surface as "every
summary failed" instead of a readable error:

* the ``*-flash-lite`` models reject ``thinking_budget=0`` with ``400 INVALID_ARGUMENT``,
  so a rejected thinking config is retried once without it and remembered per model;
* a ``429`` quota error cannot be fixed by retrying the same model seconds later, while a
  ``503`` overload can - only an overload is retried on the same model;
* thinking tokens are billed against ``max_output_tokens``, so the output budget must be
  large enough for a summary to fit next to them.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Sequence
from typing import Any, Protocol

from app.core.config import Settings

logger = logging.getLogger(__name__)

_MAX_ATTEMPTS = 3
_REQUEST_TIMEOUT_MS = 30_000
_DEFAULT_MAX_OUTPUT_TOKENS = 1024
_FALLBACK_MODELS = ("gemini-3.7-flash", "gemini-3.5-flash", "gemini-3.8-flash")

# Transient overload: another attempt on the same model is worth the wait.
_OVERLOAD_MARKERS = (
    "500",
    "502",
    "503",
    "504",
    "internal",
    "unavailable",
    "high demand",
    "overloaded",
)
# Exhausted quota: the same model keeps failing, but another one may have headroom.
_QUOTA_MARKERS = ("429", "resource_exhausted", "quota", "rate limit", "billing")
# Bad credentials or a broken client: no model works, so fail immediately.
_FATAL_MARKERS = ("api key", "permission_denied", "unauthenticated", "401", "403")
# Rejected request or unknown model: the same model will never succeed.
_INVALID_MARKERS = (
    "invalid_argument",
    "invalid argument",
    "not_found",
    "not found",
    "unsupported",
)


def _classify(exc: Exception) -> str:
    """Bucket a provider error as ``fatal``, ``quota``, ``overload``, ``invalid`` or ``other``."""
    message = f"{type(exc).__name__}: {exc}".lower()
    if any(marker in message for marker in _FATAL_MARKERS):
        return "fatal"
    if any(marker in message for marker in _QUOTA_MARKERS):
        return "quota"
    if any(marker in message for marker in _OVERLOAD_MARKERS):
        return "overload"
    if any(marker in message for marker in _INVALID_MARKERS):
        return "invalid"
    return "other"


def _finish_reason(response: object) -> str:
    """Best-effort finish reason, for the error raised when a response has no text."""
    candidates = getattr(response, "candidates", None) or []
    if not candidates:
        return "unknown"
    return str(getattr(candidates[0], "finish_reason", "unknown"))


FILE_PROMPT = (
    "You are indexing a project knowledge base. Summarise the markdown file below in "
    "1-2 sentences for someone browsing a folder tree. State what the file is about, "
    "not its formatting. Do not add commentary or repeat the filename.\n\n"
    "File: {name}\n\n---\n{text}\n---"
)

DIRECTORY_PROMPT = (
    "You are describing one folder in a project knowledge tree. Write 2-4 sentences "
    "describing what this folder and everything under it contains, for someone deciding "
    "whether to open it. Base it only on the child entries listed; never invent names.\n\n"
    "Folder: {path}\n\n"
    "Files directly inside:\n{files}\n\n"
    "Subfolders:\n{subdirectories}"
)


class Summarizer(Protocol):
    """What the service needs from a summariser."""

    model_name: str

    async def summarise_file(self, *, name: str, text: str) -> str: ...

    async def summarise_directory(
        self,
        *,
        path: str,
        files: Sequence[tuple[str, str]],
        directories: Sequence[tuple[str, str]],
    ) -> str: ...


def _bullet_list(entries: Sequence[tuple[str, str]], empty: str = "(none)") -> str:
    if not entries:
        return empty
    return "\n".join(f"- {name}: {summary}" for name, summary in entries)


class MockSummarizer:
    """Deterministic, offline summariser used by tests and keyless local runs."""

    model_name = "mock"

    async def summarise_file(self, *, name: str, text: str) -> str:
        first_line = next((line.strip(" #\t") for line in text.splitlines() if line.strip()), "")
        snippet = first_line[:120] or "no content"
        return f"{name} - {snippet}"

    async def summarise_directory(
        self,
        *,
        path: str,
        files: Sequence[tuple[str, str]],
        directories: Sequence[tuple[str, str]],
    ) -> str:
        label = path or "the project root"
        parts = [f"{label} holds {len(files)} file(s) and {len(directories)} subfolder(s)."]
        if files:
            names = ", ".join(name for name, _ in files[:5])
            parts.append(f"Files: {names}.")
        if directories:
            names = ", ".join(name for name, _ in directories[:5])
            parts.append(f"Subfolders: {names}.")
        return " ".join(parts)


class GeminiSummarizer:
    """Google Gemini implementation (``google-genai``)."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        max_output_tokens: int = _DEFAULT_MAX_OUTPUT_TOKENS,
        thinking_budget: int | None = 0,
        client: Any | None = None,
    ) -> None:
        if client is None:
            if not api_key:
                raise ValueError("GEMINI_API_KEY is required for the Gemini summariser")
            from google import genai
            from google.genai import types

            client = genai.Client(
                api_key=api_key,
                http_options=types.HttpOptions(timeout=_REQUEST_TIMEOUT_MS),
            )
        self._client = client
        self.model_name = model
        self._max_output_tokens = max_output_tokens
        self._thinking_budget = thinking_budget
        # Models that rejected a thinking config (the *-flash-lite family does).
        self._thinking_supported: dict[str, bool] = {}

    def _wants_thinking(self, model: str) -> bool:
        """Thinking is opt-in: only a positive budget is sent, and only if accepted."""
        if self._thinking_budget is None or self._thinking_budget <= 0:
            return False
        return self._thinking_supported.get(model, True)

    def _generation_config(self, *, include_thinking: bool):
        """Generation config for one call; thinking is dropped when unsupported."""
        from google.genai import types

        options: dict[str, object] = {
            "temperature": 0,
            "max_output_tokens": self._max_output_tokens,
        }
        if include_thinking and self._thinking_budget is not None:
            options["thinking_config"] = types.ThinkingConfig(thinking_budget=self._thinking_budget)
        return types.GenerateContentConfig(**options)

    def _models(self) -> tuple[str, ...]:
        """Configured model first, then other flash models when it is unavailable."""
        return (self.model_name,) + tuple(
            model for model in _FALLBACK_MODELS if model != self.model_name
        )

    async def _call(self, *, model: str, prompt: str, include_thinking: bool):
        """One request, returning the raw SDK response."""
        return await self._client.aio.models.generate_content(
            model=model,
            contents=prompt,
            config=self._generation_config(include_thinking=include_thinking),
        )

    async def _generate(self, prompt: str) -> str:
        """Call Gemini, retrying overloads and moving on to other models when needed."""
        last_error: Exception | None = None
        for model in self._models():
            for attempt in range(1, _MAX_ATTEMPTS + 1):
                include_thinking = self._wants_thinking(model)
                try:
                    response = await self._call(
                        model=model, prompt=prompt, include_thinking=include_thinking
                    )
                except Exception as exc:  # noqa: BLE001 - classified right below
                    last_error = exc
                    kind = _classify(exc)
                    if kind == "fatal":
                        raise
                    if kind == "invalid" and include_thinking:
                        # e.g. gemini-3.5-flash-lite rejects thinking_budget=0 outright.
                        logger.info(
                            "Model %s rejected the thinking config (%s); retrying without it",
                            model,
                            type(exc).__name__,
                        )
                        self._thinking_supported[model] = False
                        continue
                    if kind == "overload" and attempt < _MAX_ATTEMPTS:
                        delay = float(2 ** (attempt - 1))
                        logger.warning(
                            "Gemini call failed (%s: %s); retrying %s in %.0fs",
                            type(exc).__name__,
                            str(exc)[:200],
                            model,
                            delay,
                        )
                        await asyncio.sleep(delay)
                        continue
                    logger.warning(
                        "Model %s failed (%s: %s); trying the next model",
                        model,
                        type(exc).__name__,
                        str(exc)[:200],
                    )
                    break

                text = (getattr(response, "text", None) or "").strip()
                if text:
                    return text

                last_error = ValueError(
                    f"Gemini returned an empty summary (finish_reason={_finish_reason(response)})"
                )
                if include_thinking:
                    # Thinking tokens can consume the whole output budget.
                    self._thinking_supported[model] = False
                    continue
                logger.warning("Model %s returned no text; trying the next model", model)
                break

        raise RuntimeError("Gemini failed for every model") from last_error

    async def summarise_file(self, *, name: str, text: str) -> str:
        return await self._generate(FILE_PROMPT.format(name=name, text=text))

    async def summarise_directory(
        self,
        *,
        path: str,
        files: Sequence[tuple[str, str]],
        directories: Sequence[tuple[str, str]],
    ) -> str:
        return await self._generate(
            DIRECTORY_PROMPT.format(
                path=path or "(project root)",
                files=_bullet_list(files),
                subdirectories=_bullet_list(directories),
            )
        )


def build_summarizer(settings: Settings) -> Summarizer:
    """Pick the summariser for the current configuration."""
    if settings.resolved_summarizer == "gemini":
        return GeminiSummarizer(
            api_key=settings.gemini_api_key,
            model=settings.gemini_model,
            thinking_budget=settings.gemini_thinking_budget,
        )
    logger.info("Using the offline mock summariser (no GEMINI_API_KEY configured)")
    return MockSummarizer()
