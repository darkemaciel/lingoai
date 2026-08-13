"""Minimal in-process publish/subscribe domain event bus.

Modules communicate across bounded-context boundaries only via published
domain events (chiefly ``LearningEvent``-shaped events) or explicit
application-layer calls — never direct cross-module table joins in domain
code (Constitution §3, data-model.md's Entity Relationship Overview).

Intentionally minimal: synchronous process, in-memory, no external broker —
there is no Redis/queue in this iteration (research.md §5), and nothing in
this slice's NFRs requires one. If a future slice needs cross-process
delivery, this module is the single seam to swap for a real broker without
touching any handler's call site.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import Any

EventHandler = Callable[[Any], Awaitable[None] | None]


class EventBus:
    """Simple type-keyed pub/sub. Handlers may be sync or async callables."""

    def __init__(self) -> None:
        self._handlers: dict[type, list[EventHandler]] = defaultdict(list)

    def subscribe(self, event_type: type, handler: EventHandler) -> None:
        """Register ``handler`` to run whenever an event of exactly
        ``event_type`` is published (no inheritance-based matching, to keep
        dispatch simple and predictable)."""
        self._handlers[event_type].append(handler)

    def unsubscribe(self, event_type: type, handler: EventHandler) -> None:
        self._handlers[event_type].remove(handler)

    async def publish(self, event: Any) -> None:
        """Invoke every handler subscribed to ``type(event)``, awaiting any
        that return a coroutine. Handlers run sequentially, in subscription
        order; an exception in one handler propagates and stops the rest —
        callers that need best-effort fan-out should catch inside their own
        handler."""
        for handler in self._handlers[type(event)]:
            result = handler(event)
            if hasattr(result, "__await__"):
                await result  # type: ignore[misc]


# Process-wide default bus. Application services import this singleton
# rather than constructing their own ``EventBus``, so subscribers registered
# anywhere in the process (e.g. progression/gamification listeners on
# LearningEvent) all see the same publish stream.
event_bus = EventBus()
