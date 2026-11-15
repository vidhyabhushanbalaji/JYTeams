"""Prompt text for Graph Add.

One prompt: update the descriptions of the folders a placement touched. It is asked for JSON so
one strict parser serves it, and every folder is described in the same call — the number of
prompts per placement is one, however deep the tree.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # the describer imports this module, so only the types are needed here
    from app.graph_add.describer import DocumentContext, TargetContext

_CURRENT_CHARS = 400
_TEXT_CHARS = 4_000

REFRESH_PROMPT = (
    "You maintain the folder descriptions of a project knowledge tree. A new document has just "
    "been placed, so the folders around it need their descriptions updated. For every folder "
    "listed, write at most {max_chars} characters (about two sentences) describing what it and "
    "everything under it contains, naming the topics, tools and concepts explicitly, because a "
    "search matches this text to find the folder. Keep what is still true, add what the new "
    "document brings, and never invent names."
    "\n\n"
    "New document: {name}\n"
    "Placed in folder: {folder}\n\n"
    "Document text:\n### {name}\n{text}\n\n"
    "Folders to update, deepest first:\n{targets}\n\n"
    'Reply with JSON only, exactly: {{"descriptions": [{{"path": "operations", '
    '"description": "…"}}]}}'
)

TARGET_BLOCK = (
    "{index}. path={path}\n"
    "   current description: {current}\n"
    "   files directly inside: {files}\n"
    "   subfolders: {subfolders}"
)


def refresh_prompt(
    *,
    document: DocumentContext,
    targets: Sequence[TargetContext],
    text_limit: int = _TEXT_CHARS,
    max_chars: int = 300,
) -> str:
    """Prompt asking for the updated description of every affected folder."""
    text = document.text or ""
    if len(text) > text_limit:
        text = f"{text[:text_limit]}\n[… truncated …]"
    return REFRESH_PROMPT.format(
        name=document.name,
        folder=document.directory_path or "(project root)",
        text=text,
        max_chars=max_chars,
        targets="\n".join(
            TARGET_BLOCK.format(
                index=index,
                path=target.path or "(project root)",
                current=_short(target.current_description) or "(not described yet)",
                files=", ".join(target.files) or "(none)",
                subfolders=(
                    "; ".join(
                        f"{name}: {_short(description)}" for name, description in target.subfolders
                    )
                    or "(none)"
                ),
            )
            for index, target in enumerate(targets, start=1)
        ),
    )


def _short(text: str, limit: int = _CURRENT_CHARS) -> str:
    value = " ".join((text or "").split())
    return value if len(value) <= limit else f"{value[:limit]}…"
