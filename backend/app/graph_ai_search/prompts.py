"""Prompt text for the Graph AI Search section.

Two prompts: the per-folder judgement (which files here answer the query, which subfolders
could hide one) and the final ranking. Both ask for JSON so one strict parser serves them.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.graph_ai_search.search import DocumentBrief, FolderBrief, LoggedFile

_EXCERPT = 220

JUDGE_PROMPT = (
    "You are searching a project's documentation tree for one query.\n"
    'You are looking inside the folder "{folder}".\n\n'
    "Query: {query}\n\n"
    "Files directly inside this folder:\n{documents}\n\n"
    "Subfolders of this folder:\n{folders}\n\n"
    "Decide two things:\n"
    "1. Which files answer the query? Judge by the summary, and include a file only if a "
    "reader looking for the query would want it. relevance is 0.0-1.0; 0.6 and above is a "
    "real match, below 0.4 is unrelated.\n"
    "2. Which subfolders could contain an answer? Open a folder only if the topic plausibly "
    "lives below it, judged from its description and the names listed. List every one that "
    "qualifies — there is no limit on how many.\n"
    "Empty lists are expected when nothing qualifies. Never invent a file or folder.\n\n"
    'Reply with JSON only, exactly: {{"files": [{{"index": 1, "relevance": 0.82, '
    '"reason": "one short sentence"}}], "directories": [{{"index": 1, "relevance": 0.7, '
    '"reason": "one short sentence"}}]}}'
)

RANK_PROMPT = (
    "You are ranking documents against one search query.\n"
    "Order them by how directly they answer it: a document that answers the query completely "
    "scores near 1.0, one that merely touches the topic scores low. Judge the content "
    "described, not the wording.\n\n"
    "Query: {query}\n\n"
    "Documents:\n{documents}\n\n"
    "Return every document, with a 0.0-1.0 score and a one-sentence reason.\n\n"
    'Reply with JSON only, exactly: {{"ranking": [{{"index": 1, "score": 0.92, '
    '"reason": "one short sentence"}}]}}'
)


def judge_prompt(
    *,
    query: str,
    folder: FolderBrief,
    documents: Sequence[DocumentBrief],
    folders: Sequence[FolderBrief],
) -> str:
    """Prompt for one folder's turn in the walk."""
    return JUDGE_PROMPT.format(
        folder=folder.path or "(project root)",
        query=query,
        documents="\n".join(
            f'- "{document.name}" — {_short(document.summary)}' for document in documents
        )
        or "(no files)",
        folders="\n".join(
            f'- "{child.name}" — {_short(child.description)}'
            + (f" (holds: {', '.join(child.contains)})" if child.contains else "")
            for child in folders
        )
        or "(no subfolders)",
    )


def rank_prompt(*, query: str, documents: Sequence[LoggedFile]) -> str:
    """Prompt for the final ordering of the logged files."""
    return RANK_PROMPT.format(
        query=query,
        documents="\n".join(
            f'{index}. path="{item.document.path}" — {_short(item.document.summary)}'
            for index, item in enumerate(documents, start=1)
        ),
    )


def _short(text: str, limit: int = _EXCERPT) -> str:
    value = " ".join((text or "").split())
    return value if len(value) <= limit else f"{value[:limit]}…"
