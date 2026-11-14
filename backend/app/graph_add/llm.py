"""Navigator implementations: Gemini for real use, a deterministic mock for tests.

Both satisfy :class:`app.graph_add.navigate.Navigator`, so the traversal code never knows
which one it is talking to. The mock exists for the same reason Graph Creation has one: the
suite and a keyless local run must behave identically without a network call.
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Sequence
from typing import Any

from app.core.config import Settings
from app.graph_add import prompts
from app.graph_add.navigate import (
    CandidateContext,
    ChildBrief,
    Judgement,
    Navigator,
    RankedCandidate,
    fallback_folder_names,
)

logger = logging.getLogger(__name__)

_WORD = re.compile(r"[a-z0-9]+")
#: Filler words that carry no topic signal, kept as one string so the list stays readable.
#: The markdown suffixes are here because file names leak them into the vocabulary.
_STOPWORD_TEXT = (
    "a an and are as at be by for from has how in into is it its md mdx markdown of on or "
    "that the their this to was what when where which who why with"
)
_STOPWORDS = frozenset(_STOPWORD_TEXT.split())
_MOCK_THRESHOLD = 0.10
_MOCK_NAME_BONUS = 0.3
#: How much of a child's summary the mock quotes back when describing a folder. Long
#: enough that a refreshed description keeps its topic words (a real model rewrites prose
#: instead, so this only affects the offline fallback).
_EXCERPT = 240


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


class GeminiNavigator:
    """Google Gemini implementation (``google-genai``, already a dependency)."""

    def __init__(self, *, api_key: str, model: str, max_output_tokens: int = 768) -> None:
        if not api_key:
            raise ValueError("GEMINI_API_KEY is required for the Gemini navigator")
        from google import genai

        self._client = genai.Client(api_key=api_key)
        self.model_name = model
        self._max_output_tokens = max_output_tokens

    async def _generate(self, prompt: str, *, json_mode: bool = False) -> str:
        from google.genai import types

        config = types.GenerateContentConfig(
            temperature=0,
            max_output_tokens=self._max_output_tokens,
        )
        if json_mode:
            config.response_mime_type = "application/json"
        response = await self._client.aio.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=config,
        )
        text = (getattr(response, "text", None) or "").strip()
        if not text:
            raise ValueError("Gemini returned an empty response")
        return text

    async def summarise_file(self, *, name: str, text: str) -> str:
        return await self._generate(prompts.file_prompt(name=name, text=text))

    async def judge_children(
        self,
        *,
        file_name: str,
        summary: str,
        path: str,
        children: Sequence[ChildBrief],
    ) -> Sequence[Judgement]:
        raw = await self._generate(
            prompts.navigate_prompt(
                file_name=file_name, summary=summary, path=path, children=children
            ),
            json_mode=True,
        )
        matches = _json_object(raw).get("matches")
        if not isinstance(matches, list):
            return []

        judged: list[Judgement] = []
        for entry in matches:
            if not isinstance(entry, dict):
                continue
            index = entry.get("index")
            if not isinstance(index, int) or not 1 <= index <= len(children):
                continue
            child = children[index - 1]
            judged.append(
                Judgement(
                    directory_id=child.directory_id,
                    relevance=_unit(entry.get("relevance")),
                    reason=str(entry.get("reason") or "").strip() or "Related folder.",
                )
            )
        return judged

    async def rank(
        self,
        *,
        file_name: str,
        summary: str,
        candidates: Sequence[CandidateContext],
    ) -> Sequence[RankedCandidate]:
        raw = await self._generate(
            prompts.rank_prompt(file_name=file_name, summary=summary, candidates=candidates),
            json_mode=True,
        )
        ranking = _json_object(raw).get("ranking")
        if not isinstance(ranking, list):
            return []

        ranked: list[RankedCandidate] = []
        for entry in ranking:
            if not isinstance(entry, dict):
                continue
            index = entry.get("index")
            if not isinstance(index, int) or not 1 <= index <= len(candidates):
                continue
            names = entry.get("folder_names")
            folder_names = tuple(
                str(name).strip()
                for name in (names if isinstance(names, list) else [])
                if str(name).strip()
            )[:2]
            ranked.append(
                RankedCandidate(
                    directory_id=candidates[index - 1].node.directory_id,
                    score=_unit(entry.get("score")),
                    reason=str(entry.get("reason") or "").strip(),
                    folder_names=folder_names,
                )
            )
        return ranked

    async def describe_folder(
        self,
        *,
        path: str,
        files: Sequence[tuple[str, str]],
        directories: Sequence[tuple[str, str]],
    ) -> str:
        return await self._generate(
            prompts.folder_prompt(path=path, files=files, directories=directories)
        )


class MockNavigator:
    """Deterministic, offline navigator used by tests and keyless local runs.

    Matching is rough keyword overlap, which is enough to exercise the real traversal: the
    walk, the ranking and the folder descriptions all take the same code paths as Gemini.
    """

    model_name = "mock"

    async def summarise_file(self, *, name: str, text: str) -> str:
        body = " ".join(text.split())[:200] or "no content"
        return f"{name} — {body}"

    async def judge_children(
        self,
        *,
        file_name: str,
        summary: str,
        path: str,
        children: Sequence[ChildBrief],
    ) -> Sequence[Judgement]:
        summary_tokens = _tokens(f"{file_name} {summary}")
        judged: list[Judgement] = []
        for child in children:
            context = f"{child.name} {' '.join(child.contains)} {child.description}"
            child_tokens = _tokens(context)
            relevance = _overlap(summary_tokens, child_tokens)
            if _overlap(_tokens(file_name), child_tokens):
                relevance = min(1.0, relevance + _MOCK_NAME_BONUS)
            if relevance < _MOCK_THRESHOLD:
                continue
            judged.append(
                Judgement(
                    directory_id=child.directory_id,
                    relevance=round(relevance, 2),
                    reason=f"Shares keywords with '{child.name}'.",
                )
            )
        return judged

    async def rank(
        self,
        *,
        file_name: str,
        summary: str,
        candidates: Sequence[CandidateContext],
    ) -> Sequence[RankedCandidate]:
        summary_tokens = _tokens(f"{file_name} {summary}")
        ranked: list[RankedCandidate] = []
        for candidate in candidates:
            node = candidate.node
            context = " ".join(
                [
                    node.name,
                    node.description,
                    *node.contains,
                    *(name for name, _ in candidate.files),
                ]
            )
            score = _overlap(summary_tokens, _tokens(context))
            ranked.append(
                RankedCandidate(
                    directory_id=node.directory_id,
                    score=round(min(1.0, score), 2),
                    reason=f"Shares keywords with '{node.name}'." if score else "Weak match.",
                    folder_names=fallback_folder_names(file_name),
                )
            )
        ranked.sort(key=lambda item: (-item.score, item.directory_id))
        return ranked

    async def describe_folder(
        self,
        *,
        path: str,
        files: Sequence[tuple[str, str]],
        directories: Sequence[tuple[str, str]],
    ) -> str:
        label = path or "the project root"
        parts = [f"{label} holds {len(files)} file(s) and {len(directories)} subfolder(s)."]
        if files:
            entries = "; ".join(f"{name} ({summary[:_EXCERPT]})" for name, summary in files[:5])
            parts.append(f"Files: {entries}.")
        if directories:
            entries = "; ".join(
                f"{name} ({summary[:_EXCERPT]})" for name, summary in directories[:5]
            )
            parts.append(f"Subfolders: {entries}.")
        return " ".join(parts)


def build_navigator(settings: Settings) -> Navigator:
    """Pick the navigator for the current configuration (same switch as creation)."""
    if settings.resolved_summarizer == "gemini":
        return GeminiNavigator(api_key=settings.gemini_api_key, model=settings.gemini_model)
    logger.info("Using the offline mock navigator (no GEMINI_API_KEY configured)")
    return MockNavigator()
