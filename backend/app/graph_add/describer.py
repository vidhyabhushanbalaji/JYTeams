"""Folder describers: Gemini for real use, a deterministic mock for tests.

Graph Add no longer summarises the document it places. After a placement it asks for the updated
description of every affected folder — the new folder (if one was created), the folder it landed
in, and its ancestors — in a single call, then applies whatever comes back.
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from app.core.config import Settings
from app.graph_add import prompts

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DocumentContext:
    """The placed document: what the refreshed descriptions have to account for."""

    name: str
    directory_path: str
    text: str


@dataclass(frozen=True)
class TargetContext:
    """One folder whose description must be updated."""

    path: str
    current_description: str
    files: tuple[str, ...] = ()
    subfolders: tuple[tuple[str, str], ...] = ()


class FolderDescriber(Protocol):
    """What the service needs: updated descriptions for the folders a placement touched."""

    model_name: str

    async def update_descriptions(
        self, *, document: DocumentContext, targets: Sequence[TargetContext]
    ) -> dict[str, str]: ...


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


class GeminiFolderDescriber:
    """Google Gemini implementation (``google-genai``, already a dependency)."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        max_output_tokens: int = 1024,
        client: Any | None = None,
    ) -> None:
        if client is None:
            if not api_key:
                raise ValueError("GEMINI_API_KEY is required for the Gemini describer")
            from google import genai

            client = genai.Client(api_key=api_key)
        self._client = client
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

    async def update_descriptions(
        self, *, document: DocumentContext, targets: Sequence[TargetContext]
    ) -> dict[str, str]:
        if not targets:
            return {}
        raw = await self._generate(prompts.refresh_prompt(document=document, targets=targets))
        entries = _json_object(raw).get("descriptions")
        if not isinstance(entries, list):
            return {}

        wanted = {target.path for target in targets}
        updates: dict[str, str] = {}
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            path = str(entry.get("path") or "")
            description = " ".join(str(entry.get("description") or "").split())
            if path in wanted and description:
                updates[path] = description
        return updates


class MockFolderDescriber:
    """Deterministic, offline describer used by tests and keyless local runs.

    It names what the folder holds, the way a real model's description would, so tooling and
    tests that look for a file or subfolder name keep working without a key.
    """

    model_name = "mock"

    async def update_descriptions(
        self, *, document: DocumentContext, targets: Sequence[TargetContext]
    ) -> dict[str, str]:
        return {
            target.path: (
                f"{target.path or 'the project root'} holds {len(target.files)} file(s) and "
                f"{len(target.subfolders)} subfolder(s). "
                f"Files: {', '.join(target.files[:5]) or 'none'}. "
                f"Subfolders: "
                f"{', '.join(name for name, _ in target.subfolders[:5]) or 'none'}. "
                f"{document.name} was added here."
            )
            for target in targets
        }


def build_describer(settings: Settings) -> FolderDescriber:
    """Pick the describer for the current configuration (same switch as the other sections)."""
    if settings.resolved_summarizer == "gemini":
        return GeminiFolderDescriber(api_key=settings.gemini_api_key, model=settings.gemini_model)
    logger.info("Using the offline mock describer (no GEMINI_API_KEY configured)")
    return MockFolderDescriber()
