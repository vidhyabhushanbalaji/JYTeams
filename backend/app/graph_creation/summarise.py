"""Summarisation: one short summary per file, one description per directory.

Directories are described bottom-up: a directory's prompt is built from its child file
summaries and its child directory descriptions, so the root ends up describing the whole
project. Two implementations exist — ``GeminiSummarizer`` (real) and ``MockSummarizer``
(deterministic, no network) — selected by ``SUMMARIZER``/``GEMINI_API_KEY``.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Protocol

from app.core.config import Settings

logger = logging.getLogger(__name__)

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
        return f"{name} — {snippet}"

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

    def __init__(self, *, api_key: str, model: str, max_output_tokens: int = 256) -> None:
        if not api_key:
            raise ValueError("GEMINI_API_KEY is required for the Gemini summariser")
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
            ),
        )
        text = (getattr(response, "text", None) or "").strip()
        if not text:
            raise ValueError("Gemini returned an empty summary")
        return text

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
        return GeminiSummarizer(api_key=settings.gemini_api_key, model=settings.gemini_model)
    logger.info("Using the offline mock summariser (no GEMINI_API_KEY configured)")
    return MockSummarizer()
