"""Descriptions: one prose description per directory, written from the files inside it.

There are no per-file summaries any more. Each directory's prompt carries the *text* of the files
directly inside it (heads, capped) plus the descriptions of its child directories, and folders are
described bottom-up, so the root ends up describing the whole project. That is one model call per
directory instead of one per file plus one per directory.

Two implementations exist - ``GeminiDescriber`` (real, through ``google-genai``) and
``MockDescriber`` (deterministic, no network) - selected by ``SUMMARIZER`` and the configured
API key. Gemini is the only provider: ``GEMINI_MODEL`` (``gemini-3.1-flash-lite``) writes every
description.

Because a description is now the only thing a local search can match a folder on, the prompt asks
for the words a reader would search for (tool names, error codes, concepts) rather than a neutral
abstract.

Three provider quirks are handled here, because each of them used to surface as "every
description failed" instead of a readable error:

* a thinking config the model rejects is retried once without it and remembered per model
  (blank ``GEMINI_THINKING_LEVEL`` already sends none, which is the cheapest option);
* a ``429`` quota error cannot be fixed by retrying the same model seconds later, while a
  ``503`` overload can - only an overload is retried on the same model;
* thinking tokens are billed against ``max_output_tokens``, so the output budget must be
  large enough for a description to fit next to them.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from app.core.config import Settings
from app.core.pacing import RequestPacer
from app.core.text import clip_description

logger = logging.getLogger(__name__)

_MAX_ATTEMPTS = 3
_REQUEST_TIMEOUT_MS = 30_000
#: Thinking tokens are billed against the output budget, so leave room for a description even
#: when a thinking level is configured. The text itself is clipped to DESCRIPTION_MAX_CHARS.
_DEFAULT_MAX_OUTPUT_TOKENS = 2048
#: No fallback by default: every description is written by the configured model. Set
#: GEMINI_FALLBACK_MODELS to opt into another model when the primary one is unavailable.
_FALLBACK_MODELS: tuple[str, ...] = ()

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


DIRECTORY_PROMPT = (
    "You are describing one folder in a project knowledge tree. Write at most {max_chars} "
    "characters (about two sentences) describing what this folder and everything under it "
    "contains, for someone deciding whether to open it. Name the topics, tools, commands and "
    "concepts explicitly, because a search matches this text to find the folder. Base it only "
    "on the entries below; never invent names.\n\n"
    "Folder: {path}\n\n"
    "Files directly inside:\n{files}\n\n"
    "Subfolders:\n{subdirectories}"
)

FILE_BLOCK = "### {name}\n{text}"


@dataclass(frozen=True)
class Description:
    """One folder description, and the model that actually wrote it."""

    text: str
    model: str | None = None


class Describer(Protocol):
    """What the service needs: one description per directory, from the files inside it."""

    model_name: str

    async def describe_directory(
        self,
        *,
        path: str,
        files: Sequence[tuple[str, str]],
        directories: Sequence[tuple[str, str]],
    ) -> Description: ...


def _bullet_list(entries: Sequence[tuple[str, str]], empty: str = "(none)") -> str:
    if not entries:
        return empty
    return "\n".join(f"- {name}: {summary}" for name, summary in entries)


def _file_blocks(files: Sequence[tuple[str, str]], empty: str = "(no files)") -> str:
    """Render the files a folder holds as delimited blocks of text."""
    if not files:
        return empty
    return "\n\n".join(FILE_BLOCK.format(name=name, text=text or "(empty)") for name, text in files)


def trim_for_prompt(
    files: Sequence[tuple[str, str]], *, per_file: int, total: int
) -> list[tuple[str, str]]:
    """Shorten each file's text so the whole folder fits in one prompt.

    The share is equal rather than proportional on purpose: a folder of twenty short notes plus
    one long document should still describe the notes.
    """
    if not files:
        return []
    per_file = max(200, per_file)
    total = max(200, total)
    limit = min(per_file, max(200, total // len(files)))
    trimmed: list[tuple[str, str]] = []
    for name, text in files:
        value = text or ""
        trimmed.append(
            (name, value if len(value) <= limit else f"{value[:limit]}\n[… truncated …]")
        )
    return trimmed


def _headline(text: str) -> str:
    """First non-empty line of a document, trimmed — the mock's stand-in for real prose."""
    first = next((line.strip(" #\t") for line in (text or "").splitlines() if line.strip()), "")
    return first[:60] or "no content"


class MockDescriber:
    """Deterministic, offline describer used by tests and keyless local runs."""

    model_name = "mock"
    _max_chars = 300

    def __init__(self, *, max_chars: int = 300) -> None:
        self._max_chars = max_chars

    async def describe_directory(
        self,
        *,
        path: str,
        files: Sequence[tuple[str, str]],
        directories: Sequence[tuple[str, str]],
    ) -> Description:
        label = path or "the project root"
        parts = [f"{label} holds {len(files)} file(s) and {len(directories)} subfolder(s)."]
        if files:
            names = ", ".join(f"{name} ({_headline(text)})" for name, text in files[:5])
            parts.append(f"Files: {names}.")
        if directories:
            names = ", ".join(name for name, _ in directories[:5])
            parts.append(f"Subfolders: {names}.")
        return Description(
            text=clip_description(" ".join(parts), self._max_chars), model=self.model_name
        )


class GeminiDescriber:
    """Google Gemini implementation (``google-genai``)."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        max_output_tokens: int = _DEFAULT_MAX_OUTPUT_TOKENS,
        thinking_level: str = "",
        fallback_models: Sequence[str] | None = None,
        max_chars: int = 300,
        min_interval_seconds: float = 0.0,
        client: Any | None = None,
    ) -> None:
        if client is None:
            if not api_key:
                raise ValueError("GEMINI_API_KEY is required for the Gemini describer")
            from google import genai
            from google.genai import types

            client = genai.Client(
                api_key=api_key,
                http_options=types.HttpOptions(timeout=_REQUEST_TIMEOUT_MS),
            )
        self._client = client
        self.model_name = model
        self._max_output_tokens = max_output_tokens
        self._thinking_level = (thinking_level or "").strip().lower()
        self._max_chars = max_chars
        self._pacer = RequestPacer(min_interval_seconds)
        # Models that rejected a thinking config (older lite models do for some levels).
        self._thinking_supported: dict[str, bool] = {}
        self._fallback_models = tuple(fallback_models) if fallback_models else _FALLBACK_MODELS

    def _wants_thinking(self, model: str) -> bool:
        """Thinking is opt-in: only a configured level is sent, and only if accepted."""
        if not self._thinking_level:
            return False
        return self._thinking_supported.get(model, True)

    def _generation_config(self, *, include_thinking: bool):
        """Generation config for one call; thinking is dropped when unsupported."""
        from google.genai import types

        options: dict[str, object] = {
            "temperature": 0,
            "max_output_tokens": self._max_output_tokens,
            # Nothing here calls a function, so the SDK's automatic function calling can only
            # add latency and log noise.
            "automatic_function_calling": types.AutomaticFunctionCallingConfig(disable=True),
        }
        if include_thinking and self._thinking_level:
            options["thinking_config"] = types.ThinkingConfig(thinking_level=self._thinking_level)
        return types.GenerateContentConfig(**options)

    def _models(self) -> tuple[str, ...]:
        """Configured model first, then the configured fallbacks."""
        return (self.model_name,) + tuple(
            model for model in self._fallback_models if model != self.model_name
        )

    async def _call(self, *, model: str, prompt: str, include_thinking: bool):
        """One request, returning the raw SDK response."""
        waited = await self._pacer.wait()
        if waited:
            logger.debug("Paced %.2fs before calling %s", waited, model)
        return await self._client.aio.models.generate_content(
            model=model,
            contents=prompt,
            config=self._generation_config(include_thinking=include_thinking),
        )

    async def _generate(self, prompt: str) -> Description:
        """Call Gemini, retrying overloads and moving on to other models when needed."""
        last_error: Exception | None = None
        failures: list[str] = []
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
                    failures.append(f"{model}: {kind}: {str(exc)[:160]}")
                    if kind == "fatal":
                        raise
                    if kind == "invalid" and include_thinking:
                        # e.g. a model that does not support the configured thinking level.
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
                    return Description(text=text, model=model)

                last_error = ValueError(
                    "Gemini returned an empty description "
                    f"(finish_reason={_finish_reason(response)})"
                )
                failures.append(f"{model}: empty response")
                if include_thinking:
                    # Thinking tokens can consume the whole output budget.
                    self._thinking_supported[model] = False
                    continue
                logger.warning("Model %s returned no text; trying the next model", model)
                break

        detail = "; ".join(failures[-6:])
        raise RuntimeError(f"Gemini failed for every model: {detail}") from last_error

    async def describe_directory(
        self,
        *,
        path: str,
        files: Sequence[tuple[str, str]],
        directories: Sequence[tuple[str, str]],
    ) -> Description:
        return await self._generate(
            DIRECTORY_PROMPT.format(
                path=path or "(project root)",
                files=_file_blocks(files),
                subdirectories=_bullet_list(directories),
                max_chars=self._max_chars,
            )
        )


def build_describer(settings: Settings) -> Describer:
    """Pick the describer for the current configuration (Gemini, or the offline mock)."""
    if settings.resolved_summarizer == "gemini":
        logger.info("Using the Gemini describer (%s)", settings.gemini_model)
        return GeminiDescriber(
            api_key=settings.gemini_api_key,
            model=settings.gemini_model,
            thinking_level=settings.gemini_thinking_level,
            fallback_models=settings.gemini_models[1:],
            max_chars=settings.description_max_chars,
            min_interval_seconds=settings.llm_min_interval_seconds,
        )
    logger.info("Using the offline mock describer (no model configured)")
    return MockDescriber(max_chars=settings.description_max_chars)
