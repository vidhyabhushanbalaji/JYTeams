"""Transient transport failures are retried a couple of times, permanent ones are not."""

from __future__ import annotations

import httpx
import pytest

from app.core.retry import call_with_retries


def test_a_working_operation_is_called_once() -> None:
    calls: list[int] = []

    result = call_with_retries(lambda: calls.append(1) or "ok", sleep=lambda _: None)

    assert result == "ok"
    assert calls == [1]


def test_a_transient_error_is_retried_with_growing_delays() -> None:
    attempts: list[int] = []
    delays: list[float] = []

    def flaky() -> str:
        attempts.append(1)
        if len(attempts) < 3:
            raise httpx.ReadError("[WinError 10035] a non-blocking socket operation ...")
        return "ok"

    assert call_with_retries(flaky, sleep=delays.append) == "ok"
    assert len(attempts) == 3
    assert delays == [0.25, 0.5]


def test_a_windows_os_error_counts_as_transient() -> None:
    attempts: list[int] = []

    def flaky() -> str:
        attempts.append(1)
        if len(attempts) < 2:
            raise OSError(10035, "a non-blocking socket operation could not be completed")
        return "ok"

    assert call_with_retries(flaky, sleep=lambda _: None) == "ok"
    assert len(attempts) == 2


def test_the_attempt_budget_is_respected_and_the_last_error_wins() -> None:
    attempts: list[int] = []

    def always_fails() -> None:
        attempts.append(1)
        raise httpx.ConnectError("connection refused")

    with pytest.raises(httpx.ConnectError):
        call_with_retries(always_fails, attempts=2, sleep=lambda _: None)
    assert len(attempts) == 2


def test_a_permanent_error_is_not_retried() -> None:
    attempts: list[int] = []

    def broken() -> None:
        attempts.append(1)
        raise ValueError("the request is malformed")

    with pytest.raises(ValueError):
        call_with_retries(broken, sleep=lambda _: None)
    assert len(attempts) == 1
