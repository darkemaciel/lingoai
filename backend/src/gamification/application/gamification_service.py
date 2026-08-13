"""Gamification application service: applies one scored outcome's XP award
and streak update to a student's `GamificationProfile` (T047/T048 domain
rules), then evaluates the badge catalog (T049) and persists any newly
unlocked `BadgeAward` rows plus their `badge_awarded` `LearningEvent`s.
Used by both `conversation` (T052) and `learning_content` (T053)
application services, mirroring `progression`'s
`level_advancement_service.py` seam.

Constitution FR-18: this module never feeds back into the progression
decision — `is_first_level_advancement`/scores arrive here only as inputs
for badge/streak bookkeeping, never the reverse.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from gamification.domain.badge_rule import BadgeEvaluationContext, evaluate_badges
from gamification.domain.streak_rule import update_streak
from gamification.domain.xp_rule import calculate_xp
from gamification.infrastructure.models import Badge, BadgeAward, GamificationProfile
from shared_kernel.application.learning_event_recorder import record_learning_event
from shared_kernel.domain.enums import ActivityType
from shared_kernel.infrastructure.learning_event_model import LearningEventType


class GamificationProfileNotFoundError(Exception):
    """Raised when the student has no `GamificationProfile` row yet —
    shouldn't normally happen since US1's placement flow bootstraps one,
    but this service fails loudly rather than silently no-op-ing if that
    invariant is ever violated."""


@dataclass(frozen=True)
class GamificationDelta:
    xp_awarded: int
    xp_total: int
    streak_current: int
    badges_unlocked: list[str]


async def apply_scored_outcome(
    session_db: AsyncSession,
    *,
    user_id: uuid.UUID,
    activity_type: ActivityType,
    performance_score: float,
    at: datetime,
    user_timezone: str,
    is_first_conversation_turn: bool = False,
    is_first_level_advancement: bool = False,
) -> GamificationDelta:
    profile = await session_db.scalar(
        select(GamificationProfile).where(GamificationProfile.user_id == user_id)
    )
    if profile is None:
        raise GamificationProfileNotFoundError(f"no GamificationProfile for user={user_id}")

    xp_awarded = calculate_xp(activity_type, performance_score)
    streak_result = update_streak(
        streak_current=profile.streak_current,
        streak_last_activity_date=profile.streak_last_activity_date,
        activity_at=at,
        user_timezone=user_timezone,
    )

    profile.xp_total += xp_awarded
    profile.streak_current = streak_result.streak_current
    profile.streak_last_activity_date = streak_result.streak_last_activity_date

    already_awarded_codes = frozenset(
        (
            await session_db.scalars(
                select(Badge.code)
                .join(BadgeAward, BadgeAward.badge_id == Badge.id)
                .where(BadgeAward.user_id == user_id)
            )
        ).all()
    )
    unlocked_codes = evaluate_badges(
        BadgeEvaluationContext(
            already_awarded_codes=already_awarded_codes,
            is_first_conversation_turn=is_first_conversation_turn,
            streak_current=profile.streak_current,
            is_first_level_advancement=is_first_level_advancement,
        )
    )

    for code in unlocked_codes:
        badge_id = await session_db.scalar(select(Badge.id).where(Badge.code == code))
        if badge_id is None:
            # Catalog not seeded (e.g. a test DB without gamification/seed.py
            # having run) — skip rather than fail the whole request.
            continue
        session_db.add(BadgeAward(id=uuid.uuid4(), user_id=user_id, badge_id=badge_id))
        await record_learning_event(
            session_db,
            user_id=user_id,
            event_type=LearningEventType.BADGE_AWARDED,
            client_submission_id=uuid.uuid4(),
            payload={"badge_code": code},
        )

    return GamificationDelta(
        xp_awarded=xp_awarded,
        xp_total=profile.xp_total,
        streak_current=profile.streak_current,
        badges_unlocked=unlocked_codes,
    )
