"""Logging setup shared by the API and scripts."""

from __future__ import annotations

import logging
import sys

_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_configured = False


def configure_logging(level: str = "INFO") -> None:
    """Configure root logging once, writing plain lines to stderr."""
    global _configured
    if _configured:
        return

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter(_FORMAT))

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())

    # Third-party libraries are chatty at INFO: httpx logs every request, google-genai logs
    # its (unused) automatic function calling on every call, and both drown out our own lines.
    for noisy in ("neo4j", "httpx", "httpx2", "httpcore", "google_genai"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    _configured = True
