"""Seed data script (T043) for `learning_paths` / `units` / `activities`.

Provides at least one `writing_exercise`, `speaking_exercise`, and
`listening_exercise` Activity per skill per CEFR level, at two
`difficulty_hint` bands (lower/higher), so
`progression/application/activity_selection_service.py` (T051) has real
content to select from at any `LearnerSkillProfile.cefr_level`/
`mastery_score` combination.

Idempotent: `seed()` skips any `(skill, cefr_level)` `LearningPath` that
already exists, so it is safe to run more than once against the same
database (e.g. on every container start).

Run manually via ``docker compose exec backend python -m
learning_content.infrastructure.seed`` (see README.md).
"""

from __future__ import annotations

import asyncio
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from learning_content.infrastructure.models import Activity, LearningPath, Unit
from shared_kernel.domain.enums import ActivityType, CEFRLevel, Skill

# Exercise-bearing skills only — `reading` has no dedicated Activity.type in
# the contract (GET /activities/next only returns writing/speaking/listening
# exercises per contracts/rest-api.md); reading progress is driven by the
# placement result and the conversation loop instead.
_EXERCISE_SKILL_TYPES: dict[Skill, ActivityType] = {
    Skill.WRITING: ActivityType.WRITING_EXERCISE,
    Skill.SPEAKING: ActivityType.SPEAKING_EXERCISE,
    Skill.LISTENING: ActivityType.LISTENING_EXERCISE,
}

_DIFFICULTY_BANDS = (30, 70)


def _prompt_content(skill: Skill, level: CEFRLevel, difficulty: int) -> dict:
    return {
        "instructions": f"{skill.value.capitalize()} practice at {level.value} "
        f"(difficulty {difficulty}).",
        "rubric": {"expected_min_words": 20 if difficulty >= 50 else 10},
    }


async def seed(session: AsyncSession) -> None:
    for skill, activity_type in _EXERCISE_SKILL_TYPES.items():
        for level in CEFRLevel:
            existing = await session.scalar(
                select(LearningPath.id).where(
                    LearningPath.skill == skill, LearningPath.cefr_level == level
                )
            )
            if existing is not None:
                continue

            path = LearningPath(
                id=uuid.uuid4(),
                skill=skill,
                cefr_level=level,
                name=f"{skill.value.capitalize()} — {level.value}",
            )
            session.add(path)

            unit = Unit(
                id=uuid.uuid4(),
                learning_path_id=path.id,
                sequence_order=1,
                name=f"{skill.value.capitalize()} {level.value} — Unit 1",
            )
            session.add(unit)

            for difficulty in _DIFFICULTY_BANDS:
                session.add(
                    Activity(
                        id=uuid.uuid4(),
                        unit_id=unit.id,
                        type=activity_type,
                        prompt_content=_prompt_content(skill, level, difficulty),
                        difficulty_hint=difficulty,
                    )
                )

    await session.commit()


async def _main() -> None:
    from shared_kernel.infrastructure.db import get_session_factory

    session_factory = get_session_factory()
    async with session_factory() as session:
        await seed(session)


if __name__ == "__main__":
    asyncio.run(_main())
