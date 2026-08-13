"""Gamification domain rule (T049): badge milestone evaluation against the
`Badge` catalog (data-model.md). Pure Python — the caller (T053/T052's
application services) gathers the relevant signals from the current
request's outcome and already-awarded badges; this function only decides
which (if any) new badge codes are unlocked.

Catalog is fixed for this iteration (data-model.md "Badge" seed examples):
`first_conversation_completed`, `streak_7_days`, `first_level_advanced`.
"""

from __future__ import annotations

from dataclasses import dataclass

FIRST_CONVERSATION_COMPLETED = "first_conversation_completed"
STREAK_7_DAYS = "streak_7_days"
FIRST_LEVEL_ADVANCED = "first_level_advanced"

STREAK_BADGE_THRESHOLD = 7


@dataclass(frozen=True)
class BadgeEvaluationContext:
    """Signals evaluated after one qualifying `LearningEvent`."""

    already_awarded_codes: frozenset[str]
    is_first_conversation_turn: bool = False
    streak_current: int = 0
    is_first_level_advancement: bool = False


def evaluate_badges(context: BadgeEvaluationContext) -> list[str]:
    """Badge codes newly unlocked by `context` — idempotent, never returns
    a code already present in `already_awarded_codes` (defense in depth;
    the DB's unique (`user_id`, `badge_id`) constraint is the ultimate
    guard against double-award races)."""
    unlocked: list[str] = []

    if (
        context.is_first_conversation_turn
        and FIRST_CONVERSATION_COMPLETED not in context.already_awarded_codes
    ):
        unlocked.append(FIRST_CONVERSATION_COMPLETED)

    if (
        context.streak_current >= STREAK_BADGE_THRESHOLD
        and STREAK_7_DAYS not in context.already_awarded_codes
    ):
        unlocked.append(STREAK_7_DAYS)

    if (
        context.is_first_level_advancement
        and FIRST_LEVEL_ADVANCED not in context.already_awarded_codes
    ):
        unlocked.append(FIRST_LEVEL_ADVANCED)

    return unlocked
