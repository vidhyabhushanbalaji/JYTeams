"""Mention markers inside a chat message.

A mention is written into the body as a stable, self-describing marker::

    see @[auth.md](file:4f1c...) and @[guides](directory:9a02...)
    (also @[#12 Fix the redirect](ticket:77be...))

Keeping the kind and the id *inside* the text is what makes a message survive a rename or two
documents with the same name: the stored body is unambiguous, and the backend resolves the ids
against the message's project before the message is written (:mod:`app.chat.service`).

This module is pure: no database, no network, no model.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

#: The kinds of thing a message may point at.
MENTION_KINDS: tuple[str, ...] = ("file", "directory", "ticket")

#: `@[label](kind:id)`. The label may not contain brackets or a newline; the id is opaque.
_MARKER = re.compile(
    r"@\[(?P<label>[^\[\]\n]{1,120})\]\((?P<kind>file|directory|ticket):(?P<id>[^()\s]{1,64})\)"
)

#: A message may mention at most this many distinct things.
MAX_MENTIONS = 20


@dataclass(frozen=True, slots=True)
class Mention:
    """One reference parsed out of a message body."""

    kind: str
    id: str
    label: str

    @property
    def key(self) -> tuple[str, str]:
        return (self.kind, self.id)


def marker(kind: str, target_id: str, label: str) -> str:
    """Build the marker the composer inserts (also what the tests assert against)."""
    if kind not in MENTION_KINDS:
        raise ValueError(f"unknown mention kind: {kind}")
    safe = clean_label(label)
    return f"@[{safe}]({kind}:{target_id})"


def clean_label(label: str, *, limit: int = 120) -> str:
    """A label that cannot break a marker: no brackets, no newlines, bounded length."""
    text = " ".join((label or "").replace("[", " ").replace("]", " ").split())
    return text[:limit] or "item"


def extract(body: str) -> list[Mention]:
    """Every distinct mention in a body, in the order they first appear."""
    found: list[Mention] = []
    seen: set[tuple[str, str]] = set()
    for match in _MARKER.finditer(body or ""):
        mention = Mention(
            kind=match.group("kind"),
            id=match.group("id"),
            label=clean_label(match.group("label")),
        )
        if mention.key in seen:
            continue
        seen.add(mention.key)
        found.append(mention)
    return found


def has_marker(body: str) -> bool:
    """True when at least one well-formed marker is present (used by the tests and the UI)."""
    return bool(extract(body))


def targets_of(mentions: Iterable[Mention], kind: str) -> list[str]:
    """The ids of one kind, deduplicated and ordered."""
    seen: set[str] = set()
    ids: list[str] = []
    for mention in mentions:
        if mention.kind != kind or mention.id in seen:
            continue
        seen.add(mention.id)
        ids.append(mention.id)
    return ids
