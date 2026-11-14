"""Searcher implementations: Gemini for real use, a deterministic mock for tests.

Both satisfy :class:`app.graph_ai_search.search.Searcher`, so the walk never knows which one
it is talking to. The mock exists for the same reason the other sections have one: the suite
and a keyless run must behave identically without a network call.
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Sequence
from typing import Any

from app.core.config import Settings
from app.graph_ai_search import prompts
from app.graph_ai_search.search import (
    DocumentBrief,
    DocumentMatch,
    FileRank,
    FolderBrief,
    FolderMatch,
    FolderVerdicts,
    LoggedFile,
    Searcher,
)

logger = logging.getLogger(__name__)

_WORD = re.compile(r"[a-z0-9]+")
#: Filler words with no topic signal; the markdown suffixes leak in from file names.
_STOPWORD_TEXT = (
    "a an and are as at be by for from has how in into is it its md mdx markdown of on or "
    "that the their this to was what when where which who why with"
)
_STOPWORDS = frozenset(_STOPWORD_TEXT.split())
_MOCK_THRESHOLD = 0.10
_MOCK_NAME_BONUS = 0.3


def _tokens(text: str) -> set[str]:
    words = {word for word in _WORD.findall((text or "").lower()) if word not in _STOPWORDS}
    return {_stem(word) for word in words}


def _stem(word: str) -> str:
    """Crude plural stripping, enough for "sessions" to meet "session"."""
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def _overlap(left: set[str], right: set[str]) -> float:
    """Share of the smaller vocabulary the two texts have in common (0.0 … 1.0)."""
    if not left or not right:
        return 0.0
    return len(left & right) / max(1, min(len(left), len(right)))


def _unit(value: Any) -> float:
    """Coerce a model-provided score into ``0.0 … 1.0``."""
    try:
        number = float(value)
    except TypeError, ValueError:
        return 0.0
    return min(1.0, max(0.0, number))


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


class GeminiSearcher:
    """Google Gemini implementation (``google-genai``, already a dependency)."""

    def __init__(self, *, api_key: str, model: str, max_output_tokens: int = 1024) -> None:
        if not api_key:
            raise ValueError("GEMINI_API_KEY is required for the Gemini searcher")
        from google import genai

        self._client = genai.Client(api_key=api_key)
        self.model_name = model
        self._max_output_tokens = max_output_tokens

    async def _generate(self, prompt: str) -> str:
        from google.genai import types

        response = await self._client.aio.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0,
                max_output_tokens=self._max_output_tokens,
                response_mime_type="application/json",
            ),
        )
        text = (getattr(response, "text", None) or "").strip()
        if not text:
            raise ValueError("Gemini returned an empty response")
        return text

    async def judge(
        self,
        *,
        query: str,
        folder: FolderBrief,
        documents: Sequence[DocumentBrief],
        folders: Sequence[FolderBrief],
    ) -> FolderVerdicts:
        raw = await self._generate(
            prompts.judge_prompt(query=query, folder=folder, documents=documents, folders=folders)
        )
        payload = _json_object(raw)
        return FolderVerdicts(
            documents=tuple(_document_matches(payload.get("files"), documents)),
            folders=tuple(_folder_matches(payload.get("directories"), folders)),
        )

    async def rank(self, *, query: str, documents: Sequence[LoggedFile]) -> Sequence[FileRank]:
        raw = await self._generate(prompts.rank_prompt(query=query, documents=documents))
        ranking = _json_object(raw).get("ranking")
        if not isinstance(ranking, list):
            return []

        ranked: list[FileRank] = []
        for entry in ranking:
            if not isinstance(entry, dict):
                continue
            index = entry.get("index")
            if not isinstance(index, int) or not 1 <= index <= len(documents):
                continue
            ranked.append(
                FileRank(
                    file_id=documents[index - 1].document.file_id,
                    score=_unit(entry.get("score")),
                    reason=str(entry.get("reason") or "").strip(),
                )
            )
        return ranked


def _document_matches(payload: object, documents: Sequence[DocumentBrief]) -> list[DocumentMatch]:
    if not isinstance(payload, list):
        return []
    matches: list[DocumentMatch] = []
    for entry in payload:
        if not isinstance(entry, dict):
            continue
        index = entry.get("index")
        if not isinstance(index, int) or not 1 <= index <= len(documents):
            continue
        matches.append(
            DocumentMatch(
                file_id=documents[index - 1].file_id,
                relevance=_unit(entry.get("relevance")),
                reason=str(entry.get("reason") or "").strip(),
            )
        )
    return matches


def _folder_matches(payload: object, folders: Sequence[FolderBrief]) -> list[FolderMatch]:
    if not isinstance(payload, list):
        return []
    matches: list[FolderMatch] = []
    for entry in payload:
        if not isinstance(entry, dict):
            continue
        index = entry.get("index")
        if not isinstance(index, int) or not 1 <= index <= len(folders):
            continue
        matches.append(
            FolderMatch(
                directory_id=folders[index - 1].directory_id,
                relevance=_unit(entry.get("relevance")),
                reason=str(entry.get("reason") or "").strip(),
            )
        )
    return matches


class MockSearcher:
    """Deterministic, offline searcher used by tests and keyless runs.

    Matching is rough keyword overlap, the same tuning the Graph Add mock uses: enough to
    exercise the real walk, the fallback and the ranking without a network call.
    """

    model_name = "mock"

    async def judge(
        self,
        *,
        query: str,
        folder: FolderBrief,
        documents: Sequence[DocumentBrief],
        folders: Sequence[FolderBrief],
    ) -> FolderVerdicts:
        query_tokens = _tokens(query)
        by_name = _tokens(query)

        document_matches: list[DocumentMatch] = []
        for document in documents:
            context = _tokens(f"{document.name} {document.summary}")
            relevance = _overlap(query_tokens, context)
            if _overlap(by_name, context):
                relevance = min(1.0, relevance + _MOCK_NAME_BONUS)
            if relevance < _MOCK_THRESHOLD:
                continue
            document_matches.append(
                DocumentMatch(
                    file_id=document.file_id,
                    relevance=round(relevance, 2),
                    reason=f"Shares keywords with '{document.name}'.",
                )
            )

        folder_matches: list[FolderMatch] = []
        for child in folders:
            context = _tokens(f"{child.name} {' '.join(child.contains)} {child.description}")
            relevance = _overlap(query_tokens, context)
            if _overlap(by_name, context):
                relevance = min(1.0, relevance + _MOCK_NAME_BONUS)
            if relevance < _MOCK_THRESHOLD:
                continue
            folder_matches.append(
                FolderMatch(
                    directory_id=child.directory_id,
                    relevance=round(relevance, 2),
                    reason=f"Shares keywords with '{child.name}'.",
                )
            )

        return FolderVerdicts(documents=tuple(document_matches), folders=tuple(folder_matches))

    async def rank(self, *, query: str, documents: Sequence[LoggedFile]) -> Sequence[FileRank]:
        query_tokens = _tokens(query)
        ranked: list[FileRank] = []
        for item in documents:
            context = _tokens(f"{item.document.name} {item.document.summary}")
            score = _overlap(query_tokens, context)
            ranked.append(
                FileRank(
                    file_id=item.document.file_id,
                    score=round(min(1.0, score), 2),
                    reason=f"Shares keywords with '{item.document.name}'."
                    if score
                    else "Weak match.",
                )
            )
        ranked.sort(key=lambda item: (-item.score, item.file_id))
        return ranked


def build_searcher(settings: Settings) -> Searcher:
    """Pick the searcher for the current configuration (same switch as the other sections)."""
    if settings.resolved_summarizer == "gemini":
        return GeminiSearcher(api_key=settings.gemini_api_key, model=settings.gemini_model)
    logger.info("Using the offline mock searcher (no GEMINI_API_KEY configured)")
    return MockSearcher()
