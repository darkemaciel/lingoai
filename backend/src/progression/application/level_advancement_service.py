"""Progression application service: applies one scored outcome to a
student's `LearnerSkillProfile` via the deterministic level-advancement
domain rule (T046), and records a `level_advanced` `LearningEvent` when it
happens (data-model.md's audit trail, AC-4). Used by both `conversation`
(T052) and `learning_content` (T053) application services — the one place
that touches `LearnerSkillProfile` write logic, so both callers stay
consistent (Constitution §3: business rules only in the Domain layer,
touched through one Application-layer seam here).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from progression.domain.level_advancement_rule import (
    AccuracyWindowEntry,
    apply_scored_activity,
    performance_score_is_correct,
)
from progression.infrastructure.models import LearnerSkillProfile
from shared_kernel.application.learning_event_recorder import record_learning_event
from shared_kernel.domain.enums import CEFRLevel, Skill
from shared_kernel.infrastructure.learning_event_model import LearningEvent, LearningEventType


class LearnerSkillProfileNotFoundError(Exception):
    """Raised when the student has no `LearnerSkillProfile` row for the
    given skill yet — shouldn't normally happen since US1's placement flow
    bootstraps one row per non-null skill level before the learning loop is
    reachable, but this service fails loudly rather than silently no-op-ing
    if that invariant is ever violated."""


@dataclass(frozen=True)
class ProgressionOutcome:
    cefr_level: CEFRLevel
    mastery_score: int
    level_advanced: bool
    is_first_level_advancement: bool


async def apply_scored_outcome(
    session_db: AsyncSession,
    *,
    user_id: uuid.UUID,
    skill: Skill,
    performance_score: float,
    at: datetime,
) -> ProgressionOutcome:
    profile = await session_db.scalar(
        select(LearnerSkillProfile).where(
            LearnerSkillProfile.user_id == user_id, LearnerSkillProfile.skill == skill
        )
    )
    if profile is None:
        raise LearnerSkillProfileNotFoundError(
            f"no LearnerSkillProfile for user={user_id} skill={skill}"
        )

    window = [
        AccuracyWindowEntry(correct=entry["correct"], at=datetime.fromisoformat(entry["at"]))
        for entry in profile.accuracy_window
    ]
    result = apply_scored_activity(
        cefr_level=profile.cefr_level,
        mastery_score=profile.mastery_score,
        accuracy_window=window,
        correct=performance_score_is_correct(performance_score),
        at=at,
    )

    is_first_level_advancement = False
    if result.level_advanced:
        # Checked BEFORE this advancement is recorded below, so it reflects
        # whether any level_advanced event existed prior to this one.
        prior_advancement = await session_db.scalar(
            select(LearningEvent.id)
            .where(
                LearningEvent.user_id == user_id,
                LearningEvent.event_type == LearningEventType.LEVEL_ADVANCED,
            )
            .limit(1)
        )
        is_first_level_advancement = prior_advancement is None

    profile.cefr_level = result.cefr_level
    profile.mastery_score = result.mastery_score
    profile.accuracy_window = [
        {"correct": entry.correct, "at": entry.at.isoformat()} for entry in result.accuracy_window
    ]

    if result.level_advanced:
        await record_learning_event(
            session_db,
            user_id=user_id,
            event_type=LearningEventType.LEVEL_ADVANCED,
            client_submission_id=uuid.uuid4(),
            skill=skill,
            payload={"new_cefr_level": str(result.cefr_level)},
        )

    return ProgressionOutcome(
        cefr_level=result.cefr_level,
        mastery_score=result.mastery_score,
        level_advanced=result.level_advanced,
        is_first_level_advancement=is_first_level_advancement,
    )
