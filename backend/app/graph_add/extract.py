"""Turn a single uploaded document into prompt-ready text.

Only markdown can be *placed* semantically, because the navigator needs prose to compare
against the folder descriptions. The function still reports *why* something is unusable so
the router can answer 415 with a specific reason instead of a generic rejection.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath

MARKDOWN_SUFFIXES = frozenset({".md", ".markdown", ".mdx"})
TRUNCATION_MARKER = "\n\n[… truncated …]"


@dataclass(frozen=True)
class Extracted:
    """Result of reading one document: usable text, or a reason why not."""

    text: str | None
    reason: str = ""

    @property
    def ok(self) -> bool:
        return self.text is not None


def is_markdown(filename: str) -> bool:
    """True when the file name carries a markdown suffix."""
    return PurePosixPath(filename).suffix.lower() in MARKDOWN_SUFFIXES


def extract_text(data: bytes, *, filename: str, max_chars: int) -> Extracted:
    """Decode a markdown document, or explain why it cannot be placed."""
    suffix = PurePosixPath(filename).suffix.lower()
    if suffix not in MARKDOWN_SUFFIXES:
        return Extracted(None, f"unsupported file type {suffix or '(none)'}")

    try:
        # utf-8-sig accepts plain UTF-8 and strips a BOM (common on Windows).
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return Extracted(None, "file is not valid UTF-8")

    text = text.strip()
    if not text:
        return Extracted(None, "file is empty")

    if len(text) > max_chars:
        text = text[:max_chars] + TRUNCATION_MARKER
    return Extracted(text)
