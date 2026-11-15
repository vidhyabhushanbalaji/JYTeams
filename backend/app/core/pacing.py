"""Keep model requests to a steady cadence instead of firing them back to back.

Free tiers rate-limit aggressively, and a burst of folder descriptions can spend a whole
minute's budget in a second. One pacer is shared by every model call a client makes, so retries
and fallback models are paced too.

The clock and sleep are injectable so tests can assert the spacing without waiting.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable


class RequestPacer:
    """Reserve request slots at least ``interval`` seconds apart."""

    def __init__(
        self,
        interval: float,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._interval = max(0.0, float(interval))
        self._clock = clock
        self._sleep = sleep
        self._next_at = 0.0
        self._lock = asyncio.Lock()

    @property
    def interval(self) -> float:
        return self._interval

    async def wait(self) -> float:
        """Block until the next slot is free, returning how long it waited."""
        if self._interval <= 0:
            return 0.0
        async with self._lock:
            now = self._clock()
            delay = self._next_at - now
            if delay > 0:
                await self._sleep(delay)
                now = self._clock()
            self._next_at = now + self._interval
            return max(0.0, delay)
