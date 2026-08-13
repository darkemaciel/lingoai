"""Gamification domain rule (T047): XP formula, research.md §7.

``xp_awarded = base_xp(activity_type) * max(PERFORMANCE_SCORE_FLOOR,
performance_score)``, rounded to the nearest integer. Reuses the same
`performance_score` signal already computed for progression (one event, one
source of truth — Constitution §12) rather than a parallel scoring
pipeline. The floor guarantees participation always earns some XP, even on
a wrong answer (FR-9's "reinforce, never punish" policy).
"""

from __future__ import annotations

from shared_kernel.domain.enums import ActivityType

BASE_XP_BY_ACTIVITY_TYPE: dict[ActivityType, int] = {
    ActivityType.CONVERSATION_PROMPT: 5,
    ActivityType.WRITING_EXERCISE: 10,
    ActivityType.SPEAKING_EXERCISE: 10,
    ActivityType.LISTENING_EXERCISE: 8,
}

PERFORMANCE_SCORE_FLOOR = 0.25


def calculate_xp(activity_type: ActivityType, performance_score: float) -> int:
    """`performance_score` is expected in `[0.0, 1.0]`; the floor is applied
    regardless of how low it is (including 0.0 — a wrong answer still
    earns floor-rate XP)."""
    base_xp = BASE_XP_BY_ACTIVITY_TYPE[activity_type]
    effective_score = max(PERFORMANCE_SCORE_FLOOR, performance_score)
    return round(base_xp * effective_score)
