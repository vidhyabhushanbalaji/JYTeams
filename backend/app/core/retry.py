"""Retry a transient transport failure once or twice before giving up.

Supabase Storage is called synchronously from a threadpool, and its failures are often nobody's
fault: on Windows httpcore's sync HTTP/2 read raises ``WinError 10035`` ("a non-blocking socket
operation could not be completed immediately"), which surfaces as ``httpx.ReadError``. One such
blip used to fail an entire Graph Creation job *after* every folder had already been described
and billed, so storage calls are retried a couple of times with a short, growing delay.

Only transport errors are retried. A duplicate object, a permissions problem or a malformed
request is permanent and must fail straight away.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable, Sequence

import httpx

logger = logging.getLogger(__name__)

#: Errors worth another attempt: connection resets, read/write failures and timeouts (httpx
#: wraps them all in ``TransportError``), plus the low-level ``OSError`` underneath them, which
#: is what a Windows ``WinError 10035`` ultimately is.
TRANSIENT_ERRORS: tuple[type[BaseException], ...] = (httpx.TransportError, OSError)


def call_with_retries[T](
    operation: Callable[[], T],
    *,
    attempts: int = 3,
    base_delay: float = 0.25,
    retry_on: Sequence[type[BaseException]] = TRANSIENT_ERRORS,
    sleep: Callable[[float], None] | None = None,
) -> T:
    """Run ``operation``, retrying a transient failure up to ``attempts`` times in total.

    Delays grow exponentially from ``base_delay`` (0.25 s, 0.5 s), and the delay function is
    injectable so tests do not wait. The last error is re-raised once the budget is spent.
    """
    total = max(1, int(attempts))
    retryable = tuple(retry_on)
    wait = sleep or time.sleep
    for attempt in range(1, total + 1):
        try:
            return operation()
        except retryable as exc:
            if attempt >= total:
                raise
            delay = max(0.0, base_delay) * (2 ** (attempt - 1))
            logger.warning(
                "Transient %s (attempt %d/%d): %s; retrying in %.2fs",
                type(exc).__name__,
                attempt,
                total,
                str(exc)[:160],
                delay,
            )
            wait(delay)
    raise AssertionError("unreachable")  # pragma: no cover - the loop always returns or raises
