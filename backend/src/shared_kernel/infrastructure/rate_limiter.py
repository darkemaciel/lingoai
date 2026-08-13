"""In-memory fixed-window rate limiter (T071, Constitution §13) for
unauthenticated, abuse-prone endpoints — chiefly `identity`'s
`/auth/register`, `/auth/login`, `/auth/refresh`, which are the routes
most exposed to credential-stuffing/brute-force/spam-registration since
every other route already requires a valid bearer token.

Deliberately in-memory, not Redis-backed: this iteration is explicitly
single-instance/local-first (plan.md Scale/Scope; research.md §5 — no
cache/session store added without a justified need). A future
multi-instance deployment needing a shared limiter would swap this module
for a Redis-backed one without touching call sites (same pattern as
`shared_kernel.domain.event_bus`'s documented swap-later seam).
"""

from __future__ import annotations

import time
from collections import defaultdict
from threading import Lock

from fastapi import HTTPException, Request, status

WINDOW_SECONDS = 60
MAX_REQUESTS_PER_WINDOW = 10

_lock = Lock()
_hits: dict[str, list[float]] = defaultdict(list)


def _client_key(request: Request) -> str:
    client = request.client
    return client.host if client else "unknown"


def enforce_rate_limit(request: Request) -> None:
    """FastAPI dependency: raises `429` once the caller (keyed by client
    IP) has made `MAX_REQUESTS_PER_WINDOW` requests to a rate-limited route
    within the last `WINDOW_SECONDS`."""
    key = _client_key(request)
    now = time.monotonic()
    cutoff = now - WINDOW_SECONDS

    with _lock:
        hits = [hit for hit in _hits[key] if hit > cutoff]
        if len(hits) >= MAX_REQUESTS_PER_WINDOW:
            _hits[key] = hits
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="too many requests, please try again later",
            )
        hits.append(now)
        _hits[key] = hits


def reset_rate_limiter() -> None:
    """Test-only: clears all tracked hit history."""
    with _lock:
        _hits.clear()
