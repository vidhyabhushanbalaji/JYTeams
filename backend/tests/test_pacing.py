"""The request pacer: spacing without real sleeps."""

from __future__ import annotations

import asyncio

from app.core.pacing import RequestPacer


class _Clock:
    """A fake clock whose sleep advances time and records the waits."""

    def __init__(self) -> None:
        self.now = 0.0
        self.waits: list[float] = []

    def __call__(self) -> float:
        return self.now

    async def sleep(self, seconds: float) -> None:
        self.waits.append(seconds)
        self.now += seconds


async def test_the_first_call_is_immediate_and_the_next_waits_the_interval() -> None:
    clock = _Clock()
    pacer = RequestPacer(2.0, clock=clock, sleep=clock.sleep)

    assert await pacer.wait() == 0.0
    assert await pacer.wait() == 2.0
    assert clock.waits == [2.0]


async def test_concurrent_callers_are_still_two_seconds_apart() -> None:
    clock = _Clock()
    pacer = RequestPacer(2.0, clock=clock, sleep=clock.sleep)

    waits = await asyncio.gather(*(pacer.wait() for _ in range(3)))

    assert waits[0] == 0.0
    assert clock.waits == [2.0, 2.0]
    assert sum(clock.waits) == 4.0


async def test_zero_interval_never_waits() -> None:
    clock = _Clock()
    pacer = RequestPacer(0, clock=clock, sleep=clock.sleep)

    for _ in range(3):
        assert await pacer.wait() == 0.0
    assert clock.waits == []
