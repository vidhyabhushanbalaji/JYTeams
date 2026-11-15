"""The folder describer: one batched call, strict JSON parsing, and what the prompt carries."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

import pytest

from app.graph_add.describer import (
    DocumentContext,
    GeminiFolderDescriber,
    GroqFolderDescriber,
    MockFolderDescriber,
    TargetContext,
)


class _Models:
    """Replays scripted replies and records the prompts it was given."""

    def __init__(self, replies: list[object]) -> None:
        self.replies = list(replies)
        self.prompts: list[str] = []

    async def generate_content(self, *, model: str, contents: str, config: Any) -> Any:
        self.prompts.append(contents)
        reply = self.replies.pop(0) if len(self.replies) > 1 else self.replies[0]
        if isinstance(reply, BaseException):
            raise reply
        return SimpleNamespace(text=reply, candidates=[])


def _describer(models: _Models, *, model: str = "m") -> GeminiFolderDescriber:
    client = SimpleNamespace(aio=SimpleNamespace(models=models))
    return GeminiFolderDescriber(api_key="", model=model, client=client)


DOCUMENT = DocumentContext(
    name="rollback.md", directory_path="guides", text="# Rollback\n\nHelm rollback."
)
TARGETS = [
    TargetContext(path="guides", current_description="Deployment material.", files=("deploy.md",)),
    TargetContext(path="", current_description="The project root.", files=("README.md",)),
]


def test_requires_an_api_key_when_building_its_own_client() -> None:
    with pytest.raises(ValueError):
        GeminiFolderDescriber(api_key="", model="m")


async def test_every_target_is_updated_in_one_call() -> None:
    payload = {
        "descriptions": [
            {"path": "guides", "description": "Deployment and rollback procedures."},
            {"path": "", "description": "A project about deploying and rolling back."},
        ]
    }
    models = _Models([json.dumps(payload)])
    describer = _describer(models)

    updates = await describer.update_descriptions(document=DOCUMENT, targets=TARGETS)

    assert updates == {
        "guides": "Deployment and rollback procedures.",
        "": "A project about deploying and rolling back.",
    }
    assert len(models.prompts) == 1


async def test_unknown_paths_and_empty_descriptions_are_dropped() -> None:
    payload = {
        "descriptions": [
            {"path": "guides", "description": "Kept."},
            {"path": "elsewhere", "description": "Not a target."},
            {"path": "", "description": "   "},
            {"index": 1},
        ]
    }
    describer = _describer(_Models([json.dumps(payload)]))

    updates = await describer.update_descriptions(document=DOCUMENT, targets=TARGETS)

    assert updates == {"guides": "Kept."}


async def test_code_fences_and_prose_around_the_json_are_tolerated() -> None:
    reply = (
        'Here you go:\n```json\n{"descriptions": [{"path": "guides", "description": "Fine."}]}\n```'
    )
    describer = _describer(_Models([reply]))

    assert await describer.update_descriptions(document=DOCUMENT, targets=TARGETS) == {
        "guides": "Fine."
    }


async def test_a_non_json_reply_raises_so_the_caller_can_keep_the_old_text() -> None:
    describer = _describer(_Models(["I cannot help with that."]))

    with pytest.raises(ValueError):
        await describer.update_descriptions(document=DOCUMENT, targets=TARGETS)


async def test_no_targets_means_no_call() -> None:
    models = _Models(["unused"])

    assert await _describer(models).update_descriptions(document=DOCUMENT, targets=[]) == {}
    assert models.prompts == []


async def test_the_prompt_carries_the_document_and_the_current_descriptions() -> None:
    models = _Models([json.dumps({"descriptions": []})])

    await _describer(models).update_descriptions(document=DOCUMENT, targets=TARGETS)

    prompt = models.prompts[0]
    assert "rollback.md" in prompt
    assert "Helm rollback." in prompt
    assert "Deployment material." in prompt
    assert "path=guides" in prompt and "path=(project root)" in prompt
    assert "at most 300 characters" in prompt


async def test_a_long_description_is_clipped_to_the_character_cap() -> None:
    payload = {"descriptions": [{"path": "guides", "description": "word " * 200}]}
    describer = _describer(_Models([json.dumps(payload)]))

    updates = await describer.update_descriptions(document=DOCUMENT, targets=TARGETS)

    assert len(updates["guides"]) <= 300
    assert updates["guides"].endswith("…")


async def test_the_mock_describes_every_target() -> None:
    updates = await MockFolderDescriber().update_descriptions(document=DOCUMENT, targets=TARGETS)

    assert set(updates) == {"guides", ""}
    assert "rollback.md" in updates["guides"]


class _GroqStub:
    """Records the call and returns a fixed reply, like ``GroqClient.complete``."""

    def __init__(self, reply: str, model: str = "openai/gpt-oss-120b") -> None:
        self.reply = reply
        self.model_name = model
        self.prompts: list[str] = []
        self.json_modes: list[bool] = []

    async def complete(self, prompt: str, *, max_tokens: int = 1024, json_mode: bool = False):
        from app.core.groq import Completion

        self.prompts.append(prompt)
        self.json_modes.append(json_mode)
        return Completion(text=self.reply, model=self.model_name)


async def test_the_groq_describer_asks_for_json_and_parses_it() -> None:
    payload = {"descriptions": [{"path": "guides", "description": "Deployment and rollback."}]}
    stub = _GroqStub(json.dumps(payload))
    describer = GroqFolderDescriber(api_key="", model="openai/gpt-oss-120b", client=stub)

    updates = await describer.update_descriptions(document=DOCUMENT, targets=TARGETS)

    assert updates == {"guides": "Deployment and rollback."}
    assert stub.json_modes == [True]
    assert "rollback.md" in stub.prompts[0]
    assert "Deployment material." in stub.prompts[0]
