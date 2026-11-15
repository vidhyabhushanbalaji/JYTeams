"""The placement prompt: one call that refreshes every affected folder, in plain prose."""

from __future__ import annotations

from app.graph_add.describer import DocumentContext, TargetContext
from app.graph_add.prompts import refresh_prompt


def test_the_prompt_asks_for_plain_prose_without_compound_identifiers() -> None:
    prompt = refresh_prompt(
        document=DocumentContext(
            name="rollback-runbook.md",
            text="# Rollback runbook\n\nRevert a release.",
            directory_path="operations",
        ),
        targets=[TargetContext(path="operations", current_description="Recovery steps.", files=())],
    )

    assert "never use hyphens, underscores or run-together identifiers" in prompt
    assert "'rollback plan', not 'rollback-plan'" in prompt
    assert "reply with json only" in prompt.lower()
