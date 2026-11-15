"""The numbers a ticket keeps: what it searched for, and when that answer goes stale.

A ticket identifies its files with one Graph AI Search run, made the first time it is opened.
Those results are stored on the ticket row, so opening it again is a database read instead of a
tree walk.

There are two caches, because two different things can change:

* **the search terms** — one short query distilled from the ticket's wording by
  :mod:`app.tickets.distill`. ``terms_fingerprint`` covers the title, the description and the
  distiller's version, so a wording change (or a new distiller) asks the model again and nothing
  else does.
* **the results** — ``fingerprint`` covers the distilled query and its points, the project's
  documents, the result limit, the folder threshold and the matcher version. A document added or
  edited re-runs the (model-free) search without a second model call.

Both hashes are deliberately cheap: a wording comparison and a document count plus the newest
``files.updated_at``, not every row.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from typing import Any

Row = dict[str, Any]

#: Graph AI Search refuses a query shorter than three characters.
MIN_QUERY_CHARS = 3
#: Files a ticket shows. Enough to cover the useful ones without turning the panel into a list.
FILE_LIMIT = 5
#: Graph AI Search's own cap for the extra context it accepts.
CONTEXT_MAX_CHARS = 500
#: Words taken from a description when the title is too short to be a query.
_FALLBACK_QUERY_WORDS = 12
#: Bumped together with ``ScoreConfig.version``: a cache written by another matcher must not be
#: reused, so raising this recomputes every stored ticket result exactly once.
MATCHING_VERSION = "local-2"
#: Bumped when the distillation prompt or :mod:`app.tickets.distill` changes: a query written by an
#: older distiller must not be reused, so raising this re-distils every ticket exactly once.
DISTILLER_VERSION = "distil-1"


def file_signature(files: Sequence[Row]) -> str:
    """``<count>:<newest updated_at>`` over a project's documents."""
    count = len(files)
    newest = max((str(row.get("updated_at") or "") for row in files), default="")
    return f"{count}:{newest}"


def terms_fingerprint(
    *,
    title: str,
    description: str,
    distiller_version: str = DISTILLER_VERSION,
) -> str:
    """Identify the ticket wording a stored query was distilled from.

    Any change to the title, the description or the distiller's version produces a different
    digest, so stale search terms can never be reused silently.
    """
    material = "\x00".join(
        (
            " ".join((title or "").split()),
            " ".join((description or "").split()),
            distiller_version,
        )
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def fingerprint(
    *,
    query: str,
    context: str = "",
    files: Sequence[Row],
    limit: int = FILE_LIMIT,
    folder_threshold: float,
    matching_version: str = MATCHING_VERSION,
    distiller_version: str = DISTILLER_VERSION,
) -> str:
    """Identify the exact question and corpus a cached result belongs to.

    Any change to the distilled query or its context, the document set, the result limit, the
    scorer's folder threshold, the matcher version or the distiller version produces a different
    digest, so a stale cache cannot be served silently.
    """
    material = "\x00".join(
        (
            " ".join((query or "").split()),
            " ".join((context or "").split()),
            file_signature(files),
            str(limit),
            f"{folder_threshold:.4f}",
            matching_version,
            distiller_version,
        )
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def search_query(title: str, description: str) -> tuple[str, str, str | None]:
    """The ``(query, context, reason)`` a ticket's search should use.

    ``reason`` is set when there is nothing worth searching for, which is the only case where a
    ticket shows no suggested files. The context is trimmed to the search endpoint's own cap.
    """
    cleaned_title = " ".join((title or "").split())
    cleaned_description = " ".join((description or "").split())
    context = cleaned_description[:CONTEXT_MAX_CHARS]

    if len(cleaned_title) >= MIN_QUERY_CHARS:
        return cleaned_title, context, None

    fallback = " ".join(cleaned_description.split()[:_FALLBACK_QUERY_WORDS])
    if len(fallback) >= MIN_QUERY_CHARS:
        return fallback, context, None
    return "", context, "Add a description and the files for this ticket can be found."
