"""Mention markers inside a chat message.

A mention is written into the body as a stable, self-describing marker::

    see @[auth.md](file:4f1c...) and @[guides](directory:9a02...)
    (also @[#12 Fix the redirect](ticket:77be...) or @[Kickoff](event:1c2d...))

Keeping the kind and the id *inside* the text is what makes a message survive a rename or two
documents with the same name: the stored body is unambiguous, and the backend resolves the ids
against the message's project before the message is written (:mod:`app.chat.service`).

The grammar itself lives in :mod:`app.core.mentions`, because a calendar event's notes write the
same markers; this module is the chat section's import site and re-exports it unchanged.
"""

from __future__ import annotations

from app.core.mentions import (
    MAX_MENTIONS,
    MENTION_KINDS,
    Mention,
    clean_label,
    extract,
    has_marker,
    marker,
    targets_of,
)

__all__ = [
    "MAX_MENTIONS",
    "MENTION_KINDS",
    "Mention",
    "clean_label",
    "extract",
    "has_marker",
    "marker",
    "targets_of",
]
