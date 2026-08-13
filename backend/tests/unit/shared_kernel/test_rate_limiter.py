"""Unit test (T071): in-memory rate limiter — allows up to the configured
limit, then raises 429; per-client-IP isolation; window reset. Pure, no
DB/HTTP server needed (uses a minimal request stand-in).
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from shared_kernel.infrastructure.rate_limiter import (
    MAX_REQUESTS_PER_WINDOW,
    enforce_rate_limit,
    reset_rate_limiter,
)


def _request(ip: str = "1.2.3.4") -> SimpleNamespace:
    return SimpleNamespace(client=SimpleNamespace(host=ip))


@pytest.fixture(autouse=True)
def _reset() -> None:
    reset_rate_limiter()


class TestEnforceRateLimit:
    def test_allows_requests_up_to_the_limit(self) -> None:
        for _ in range(MAX_REQUESTS_PER_WINDOW):
            enforce_rate_limit(_request())  # should not raise

    def test_raises_429_once_limit_exceeded(self) -> None:
        for _ in range(MAX_REQUESTS_PER_WINDOW):
            enforce_rate_limit(_request())
        with pytest.raises(HTTPException) as exc_info:
            enforce_rate_limit(_request())
        assert exc_info.value.status_code == 429

    def test_different_clients_are_tracked_independently(self) -> None:
        for _ in range(MAX_REQUESTS_PER_WINDOW):
            enforce_rate_limit(_request("1.1.1.1"))
        # A different client IP has its own budget, unaffected by the first.
        enforce_rate_limit(_request("2.2.2.2"))

    def test_reset_clears_tracked_history(self) -> None:
        for _ in range(MAX_REQUESTS_PER_WINDOW):
            enforce_rate_limit(_request())
        reset_rate_limiter()
        enforce_rate_limit(_request())  # should not raise after reset
