"""Turning a ticket into the few words a document search should use.

A ticket is written for people: it carries questions, process verbs, dates, names and acceptance
criteria. Graph AI Search scores a query by *coverage* — the share of its terms a folder or
document contains — so every word that no document could contain makes every score worse. A
500-character description therefore hides the two words that matter.

This module reduces one ticket to that handful of words, in one model call::

    "Review whether decision rights are still accurate"  ->  "decision rights accurate"

Two implementations exist, chosen the same way as the describers elsewhere in the app:

* :class:`GeminiDistiller` — real, through ``google-genai`` (``gemini-3.1-flash-lite``);
* :class:`LocalDistiller` — deterministic and offline, used by tests, keyless runs and
  ``SUMMARIZER=mock``.

Neither writes anything. The caller (``TicketService``) caches the result on the ticket row and
falls back to :func:`app.tickets.cache.search_query` if a model call fails, so a ticket always
opens.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from app.core.config import Settings
from app.core.pacing import RequestPacer
from app.core.text import keywords

logger = logging.getLogger(__name__)

#: Graph AI Search refuses a query shorter than this; a distilled query must clear the same bar.
MIN_QUERY_CHARS = 3
#: The long side of the search request. A distilled query is a phrase, not a description.
MAX_QUERY_CHARS = 200
#: Key points carried as the search's context, and the cap Graph AI Search puts on that context.
MAX_POINTS = 5
POINT_MAX_CHARS = 60
CONTEXT_MAX_CHARS = 500
#: Characters of a ticket sent to the model. The schema already caps a description at 5 000.
MAX_TICKET_CHARS = 4_000
_MAX_ATTEMPTS = 2
_REQUEST_TIMEOUT_MS = 30_000
#: Enough for a short phrase plus a few points; thinking is never requested, so this is all output.
_MAX_OUTPUT_TOKENS = 256

#: Asked for as JSON so one strict parser serves it. The worked example is the behaviour that
#: matters most: a question about a document's accuracy is a search for *decision rights*.
DISTILL_PROMPT = (
    "You prepare a work ticket for a document search. The search scores documents by how many of "
    "the query's words they contain, so every extra word makes the search worse. Reduce the "
    "ticket to the words a project document about it would actually use.\n\n"
    "Rules:\n"
    "- Keep product, module, feature, process and error-code names exactly as written.\n"
    "- Drop questions, task verbs (review, check, update, fix, investigate), dates, people, "
    "customer names, acceptance criteria, steps to reproduce and anything that talks about the "
    "ticket itself.\n"
    "- Never invent a term that is not in the ticket, and keep the ticket's own words: do not swap "
    "in synonyms and do not change a word's form (write 'accurate', not 'accuracy').\n"
    "- 'query' is 2 to 8 words, no punctuation, lower case unless it is a proper noun.\n"
    "- 'terms' is up to 5 short key points (at most 60 characters each) naming the subjects the "
    "documents should cover.\n\n"
    "Example ticket: 'Review whether decision rights are still accurate'\n"
    'Example reply: {{"query": "decision rights accurate", "terms": ["decision rights", '
    '"approval authority", "who decides what"]}}\n\n'
    "Ticket title: {title}\n"
    "Ticket description: {description}\n\n"
    'Reply with JSON only, exactly: {{"query": "…", "terms": ["…"]}}'
)

#: Words that say what to do with a ticket rather than what it is about. Kept out of the offline
#: distiller's query; a model recognises far more of them, which is why it is only a fallback.
_FILLER_TEXT = (
    "a acceptance ac acs actual add address adjust after again against all also analyse analyze "
    "answer any apply are assess assigned before bug change check clarify collect compare "
    "complete confirm consider correct could create current currently decide define delete "
    "describe description determine discuss document done double ensure evaluate examine expected "
    "explain feature figure find fix follow following gather get give handle help how identify if "
    "implement improve include investigate issue issues it jira just keep look make may might must "
    "need needs note notes now offer once only our out please possible prepare provide question "
    "raise read remove reorder reproduce required requirement requirements resolve review revisit "
    "see should since so some steps still story summary sure task team test testing that the then "
    "there these they this ticket tickets to todo try understand update use validate verify want "
    "was we were what when where whether which who why will with work would"
)
_FILLER = frozenset(_FILLER_TEXT.split())


@dataclass(frozen=True)
class SearchTerms:
    """What one ticket was reduced to: the search query, and the points behind it."""

    query: str
    points: tuple[str, ...] = ()
    model: str | None = None


class TicketDistiller(Protocol):
    """What the tickets section needs: the search terms for one ticket's wording."""

    model_name: str

    async def terms(self, *, title: str, description: str) -> SearchTerms: ...


def _collapse(text: object, limit: int) -> str:
    """Whitespace-collapsed, clipped to ``limit`` characters."""
    value = " ".join(str(text or "").split())
    return value if len(value) <= limit else value[:limit].rstrip()


def _points_from(value: object) -> tuple[str, ...]:
    """Up to :data:`MAX_POINTS` non-empty points, each clipped, deduplicated."""
    if not isinstance(value, list):
        return ()
    points: list[str] = []
    seen: set[str] = set()
    for entry in value:
        point = _collapse(entry, POINT_MAX_CHARS)
        key = point.casefold()
        if point and key not in seen:
            seen.add(key)
            points.append(point)
        if len(points) == MAX_POINTS:
            break
    return tuple(points)


def context_from(terms: SearchTerms) -> str:
    """The search's ``context``: the points joined and clipped to the endpoint's own cap."""
    return _collapse(" · ".join(terms.points), CONTEXT_MAX_CHARS)


def searchable(terms: SearchTerms) -> bool:
    """True when the distilled terms are long enough for Graph AI Search to accept them."""
    return len(terms.query) >= MIN_QUERY_CHARS


def _json_object(text: str) -> dict[str, Any]:
    """Parse a JSON object out of a model reply, tolerating code fences and prose."""
    cleaned = (text or "").strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("the model did not return a JSON object")
    payload = json.loads(cleaned[start : end + 1])
    if not isinstance(payload, dict):
        raise ValueError("the model did not return a JSON object")
    return payload


def terms_from_reply(reply: str, *, model: str | None = None) -> SearchTerms:
    """Turn one JSON reply into :class:`SearchTerms`, or raise if it holds nothing usable."""
    payload = _json_object(reply)
    query = _collapse(payload.get("query"), MAX_QUERY_CHARS)
    points = _points_from(payload.get("terms", payload.get("points")))
    if len(query) < MIN_QUERY_CHARS:
        raise ValueError("the model returned no usable search query")
    return SearchTerms(query=query, points=points, model=model)


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
# Bad credentials or a rejected request: another attempt cannot help.
_FATAL_MARKERS = (
    "api key",
    "permission_denied",
    "unauthenticated",
    "401",
    "403",
    "invalid_argument",
    "invalid argument",
    "unsupported",
)


def _overloaded(exc: Exception) -> bool:
    message = f"{type(exc).__name__}: {exc}".lower()
    return any(marker in message for marker in _OVERLOAD_MARKERS)


def _fatal(exc: Exception) -> bool:
    message = f"{type(exc).__name__}: {exc}".lower()
    return any(marker in message for marker in _FATAL_MARKERS)


class GeminiDistiller:
    """Google Gemini implementation (``google-genai``, already a dependency).

    Thinking is never configured: extracting a few words needs no reasoning, and sending no
    thinking config is the cheapest, fastest and most widely supported option.
    """

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        fallback_models: Sequence[str] | None = None,
        min_interval_seconds: float = 0.0,
        max_output_tokens: int = _MAX_OUTPUT_TOKENS,
        client: Any | None = None,
    ) -> None:
        if client is None:
            if not api_key:
                raise ValueError("GEMINI_API_KEY is required for the Gemini distiller")
            from google import genai
            from google.genai import types

            client = genai.Client(
                api_key=api_key,
                http_options=types.HttpOptions(timeout=_REQUEST_TIMEOUT_MS),
            )
        self._client = client
        self.model_name = model
        self._fallback_models = tuple(fallback_models or ())
        self._max_output_tokens = max_output_tokens
        self._pacer = RequestPacer(min_interval_seconds)

    def _models(self) -> tuple[str, ...]:
        """Configured model first, then the configured fallbacks."""
        return (self.model_name,) + tuple(
            model for model in self._fallback_models if model != self.model_name
        )

    async def _call(self, *, model: str, prompt: str):
        """One request, returning the raw SDK response."""
        from google.genai import types

        waited = await self._pacer.wait()
        if waited:
            logger.debug("Paced %.2fs before distilling with %s", waited, model)
        return await self._client.aio.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0,
                max_output_tokens=self._max_output_tokens,
                response_mime_type="application/json",
                # No tools are declared, so automatic function calling is pure overhead.
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
            ),
        )

    async def terms(self, *, title: str, description: str) -> SearchTerms:
        """One ticket, reduced to its search terms. Raises when no model answers usefully."""
        prompt = DISTILL_PROMPT.format(
            title=_collapse(title, MAX_QUERY_CHARS) or "(no title)",
            description=_collapse(description, MAX_TICKET_CHARS) or "(no description)",
        )
        last_error: Exception | None = None
        failures: list[str] = []
        for model in self._models():
            for attempt in range(1, _MAX_ATTEMPTS + 1):
                try:
                    response = await self._call(model=model, prompt=prompt)
                except Exception as exc:  # noqa: BLE001 - classified right below
                    last_error = exc
                    failures.append(f"{model}: {type(exc).__name__}: {str(exc)[:160]}")
                    if _fatal(exc):
                        raise
                    if _overloaded(exc) and attempt < _MAX_ATTEMPTS:
                        delay = float(2 ** (attempt - 1))
                        logger.warning(
                            "Gemini distillation failed (%s); retrying %s in %.0fs",
                            type(exc).__name__,
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
                if not text:
                    last_error = ValueError("Gemini returned an empty search query")
                    failures.append(f"{model}: empty response")
                    break
                return terms_from_reply(text, model=model)

        detail = "; ".join(failures[-4:])
        raise RuntimeError(f"Gemini failed to distil the ticket: {detail}") from last_error


class LocalDistiller:
    """Deterministic, offline distiller used by tests and keyless local runs.

    It keeps the ticket's most frequent content words and drops the words that describe the work
    ("review", "whether", "update") rather than its subject — the same reduction a model makes,
    minus the judgement. It adds no points: inventing context offline would be noise.
    """

    model_name = "local"

    def __init__(self, *, max_words: int = 6) -> None:
        self._max_words = max(1, max_words)

    async def terms(self, *, title: str, description: str) -> SearchTerms:
        """The ticket's content words, filler removed; raises when nothing is left."""
        words = keywords(f"{title or ''} {description or ''}", limit=24)
        kept = [word for word in words if word.lower() not in _FILLER][: self._max_words]
        query = _collapse(" ".join(kept), MAX_QUERY_CHARS)
        if len(query) < MIN_QUERY_CHARS:
            raise ValueError("the ticket has no words worth searching for")
        return SearchTerms(query=query, model=self.model_name)


def build_distiller(settings: Settings) -> TicketDistiller:
    """Pick the distiller for the current configuration (Gemini, or the offline local one)."""
    if settings.resolved_summarizer == "gemini":
        logger.info("Using the Gemini ticket distiller (%s)", settings.gemini_model)
        return GeminiDistiller(
            api_key=settings.gemini_api_key,
            model=settings.gemini_model,
            fallback_models=settings.gemini_models[1:],
            min_interval_seconds=settings.llm_min_interval_seconds,
        )
    logger.info("Using the offline local ticket distiller (no model configured)")
    return LocalDistiller()
