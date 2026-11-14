"""Prompt text for the Graph Add navigator.

Kept apart from ``llm.py`` so the wording can be reviewed on its own: the walk and the
consolidation differ in what the model is asked to decide, and both are asked for JSON so
one strict parser serves them.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.graph_add.navigate import CandidateContext, ChildBrief

_SUMMARY_CHARS = 160

FILE_PROMPT = (
    "You are indexing a project knowledge base. Summarise the markdown file below in "
    "1-2 sentences for someone deciding where it belongs in a folder tree. State what the "
    "document is about, not its formatting. Do not add commentary or repeat the filename.\n\n"
    "File: {name}\n\n---\n{text}\n---"
)

NAVIGATE_PROMPT = (
    "You are filing one new markdown document into an existing project folder tree.\n"
    "Decide which of the folders listed below the document plausibly belongs in.\n\n"
    "New document: {file_name}\n"
    "What it is about: {summary}\n\n"
    'Folders directly inside "{folder}":\n{children}\n\n'
    "Rules:\n"
    "- Judge by topic and purpose, not by wording overlap alone.\n"
    "- Only include a folder a knowledgeable reader would open to find this document.\n"
    "- relevance is 0.0-1.0; 0.6 and above is a real match, below 0.4 is unrelated.\n"
    "- If no folder is a plausible home, return an empty matches list.\n\n"
    'Reply with JSON only, exactly: {{"matches": [{{"index": 1, "relevance": 0.82, '
    '"reason": "one short sentence"}}]}}'
)

RANK_PROMPT = (
    "You are ranking candidate folders for one new markdown document.\n"
    "Prefer the most specific folder that clearly covers the document; extra depth is not a\n"
    "reason to prefer a folder, and a near-duplicate of an existing file is still a valid\n"
    "home.\n\n"
    "New document: {file_name}\n"
    "What it is about: {summary}\n\n"
    "Candidates:\n{candidates}\n\n"
    "For every candidate return its index, a 0.0-1.0 score, a one-sentence reason, and up to\n"
    "two folder names that would suit creating a new subfolder for this document.\n\n"
    'Reply with JSON only, exactly: {{"ranking": [{{"index": 1, "score": 0.9, '
    '"reason": "one short sentence", "folder_names": ["name", "other name"]}}]}}'
)

FOLDER_PROMPT = (
    "You are describing one folder in a project knowledge tree. Write 2-4 sentences "
    "describing what this folder and everything under it contains, for someone deciding "
    "whether to open it. Base it only on the child entries listed; never invent names.\n\n"
    "Folder: {path}\n\n"
    "Files directly inside:\n{files}\n\n"
    "Subfolders:\n{subdirectories}"
)


def file_prompt(*, name: str, text: str) -> str:
    """Prompt for the one-line summary of the uploaded document."""
    return FILE_PROMPT.format(name=name, text=text)


def navigate_prompt(
    *, file_name: str, summary: str, path: str, children: Sequence[ChildBrief]
) -> str:
    """Prompt asking which child folders relate to the document."""
    listing = "\n".join(_child_block(index, child) for index, child in enumerate(children, start=1))
    return NAVIGATE_PROMPT.format(
        file_name=file_name,
        summary=summary,
        folder=path or "(project root)",
        children=listing,
    )


def rank_prompt(*, file_name: str, summary: str, candidates: Sequence[CandidateContext]) -> str:
    """Prompt asking for the final, comparable ordering of the shortlist."""
    return RANK_PROMPT.format(
        file_name=file_name,
        summary=summary,
        candidates="\n".join(
            _candidate_block(index, candidate)
            for index, candidate in enumerate(candidates, start=1)
        ),
    )


def folder_prompt(
    *, path: str, files: Sequence[tuple[str, str]], directories: Sequence[tuple[str, str]]
) -> str:
    """Prompt describing a folder from the entries directly inside it."""
    return FOLDER_PROMPT.format(
        path=path or "(project root)",
        files=_bullet_list(files),
        subdirectories=_bullet_list(directories),
    )


def _child_block(index: int, child: ChildBrief) -> str:
    line = (
        f'{index}. "{child.name}" ({child.direct_file_count} file(s), '
        f"{child.child_directory_count} subfolder(s))"
    )
    lines = [line, f"   description: {_short(child.description)}"]
    if child.contains:
        lines.append(f"   contains: {', '.join(child.contains)}")
    return "\n".join(lines)


def _candidate_block(index: int, candidate: CandidateContext) -> str:
    node = candidate.node
    lines = [
        f'{index}. path="{node.path or "(project root)"}" ({node.direct_file_count} file(s), '
        f"{node.child_directory_count} subfolder(s))",
        f"   description: {_short(node.description)}",
    ]
    if node.contains:
        lines.append(f"   contains: {', '.join(node.contains)}")
    if candidate.files:
        sample = "; ".join(
            f"{name}: {_short(summary, 100)}" for name, summary in candidate.files[:5]
        )
        lines.append(f"   files inside: {sample}")
    return "\n".join(lines)


def _bullet_list(entries: Sequence[tuple[str, str]], empty: str = "(none)") -> str:
    if not entries:
        return empty
    return "\n".join(f"- {name}: {_short(summary)}" for name, summary in entries)


def _short(text: str, limit: int = _SUMMARY_CHARS) -> str:
    value = " ".join((text or "").split())
    return value if len(value) <= limit else f"{value[:limit]}…"
