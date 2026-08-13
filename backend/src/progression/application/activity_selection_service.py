"""Progression application service (T051): next-activity selection from
`LearnerSkillProfile.mastery_score`/`cefr_level` (FR-7). Backs
`GET /api/v1/activities/next`.

Deterministic, no randomness (reproducible in tests): the exercise skill
(writing/speaking/listening — `reading` has no dedicated Activity.type per
contracts/rest-api.md) with the lowest `mastery_score` is served next, so
weaker skills get more reinforcement practice. Within that skill's
`LearningPath` at the student's current `cefr_level`, the Activity whose
`difficulty_hint` is closest to a target band (30 below mastery_score=50,
70 at/above) is picked.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

import sqlalchemy as sa
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from learning_content.infrastructure.models import Activity, LearningPath, Unit
from progression.infrastructure.models import LearnerSkillProfile
from shared_kernel.domain.enums import ActivityType, Skill

_EXERCISE_SKILLS: tuple[Skill, ...] = (Skill.WRITING, Skill.SPEAKING, Skill.LISTENING)
_DIFFICULTY_BAND_SPLIT = 50
_LOW_DIFFICULTY_TARGET = 30
_HIGH_DIFFICULTY_TARGET = 70


class NoActivityAvailableError(Exception):
    """Raised when the student has no exercise-skill `LearnerSkillProfile`
    rows yet, or no seeded `Activity` matches their current level (content
    gap for that skill/CEFR-level combination)."""


@dataclass(frozen=True)
class NextActivity:
    activity_id: uuid.UUID
    type: ActivityType
    skill: Skill
    prompt_content: dict


async def select_next_activity(session_db: AsyncSession, user_id: uuid.UUID) -> NextActivity:
    profiles = (
        (
            await session_db.execute(
                select(LearnerSkillProfile).where(
                    LearnerSkillProfile.user_id == user_id,
                    LearnerSkillProfile.skill.in_(_EXERCISE_SKILLS),
                )
            )
        )
        .scalars()
        .all()
    )
    if not profiles:
        raise NoActivityAvailableError(
            f"no exercise-skill LearnerSkillProfile rows for user={user_id}"
        )

    weakest = min(profiles, key=lambda profile: (profile.mastery_score, profile.skill.value))
    target_difficulty = (
        _LOW_DIFFICULTY_TARGET
        if weakest.mastery_score < _DIFFICULTY_BAND_SPLIT
        else _HIGH_DIFFICULTY_TARGET
    )

    activity = await session_db.scalar(
        select(Activity)
        .join(Unit, Activity.unit_id == Unit.id)
        .join(LearningPath, Unit.learning_path_id == LearningPath.id)
        .where(
            LearningPath.skill == weakest.skill,
            LearningPath.cefr_level == weakest.cefr_level,
        )
        .order_by(sa.func.abs(Activity.difficulty_hint - target_difficulty))
        .limit(1)
    )
    if activity is None:
        raise NoActivityAvailableError(
            f"no seeded Activity for skill={weakest.skill} level={weakest.cefr_level}"
        )

    return NextActivity(
        activity_id=activity.id,
        type=activity.type,
        skill=weakest.skill,
        prompt_content=activity.prompt_content,
    )
