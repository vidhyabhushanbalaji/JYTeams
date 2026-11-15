"""Local matching for Graph Add: which folder does this document belong in?

The scanner is the same algorithm Graph AI Search uses (:mod:`app.core.text`), applied to folder
descriptions instead of document bodies, so a document is offered the folders a search would
look in. Nothing here calls a model.

A whole document is a poor query — a long body dilutes every comparison — so the document is
reduced to its name, headings and most frequent terms before scoring.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.core.text import Query, build_query, headings, keywords

#: Terms kept from a document when it is used as a query.
QUERY_TERM_BUDGET = 40
#: Terms kept from the surrounding context (a ticket's description, say) when it is scored
#: alongside the document. A short list is deliberate: context is a hint, not the subject.
CONTEXT_TERM_BUDGET = 24


def document_query(*, file_name: str, text: str, corpus: Sequence[str] = ()) -> Query:
    """A compact query describing one uploaded document.

    ``corpus`` is the project's own vocabulary (folder names, descriptions, file names), so rare
    terms in the document weigh more than words every folder already contains.
    """
    title = headings(text)[:2]
    stem = file_name.rsplit(".", 1)[0]
    words = " ".join(stem.replace("_", " ").replace("-", " ").split())
    body = " ".join(keywords(text, limit=QUERY_TERM_BUDGET))
    return build_query(" ".join([*title, words, body]).strip(), corpus=corpus)


def context_query(text: str, corpus: Sequence[str] = ()) -> Query | None:
    """A second query built from surrounding context — a ticket's title and description.

    It is scored *alongside* the document query rather than merged into it, because a merged
    query would dilute the document's own coverage of every folder. ``None`` when the context
    carries no usable terms.
    """
    words = " ".join(keywords(text, limit=CONTEXT_TERM_BUDGET)).strip()
    if not words:
        return None
    return build_query(words, corpus=corpus)
