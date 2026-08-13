"""Badge catalog seed data (T045) — data-model.md's three example codes,
matching the fixed set `gamification/domain/badge_rule.py` evaluates
against this iteration. Idempotent: skips any `code` that already exists.

Run manually via ``docker compose exec backend python -m
gamification.infrastructure.seed`` (see README.md).
"""

from __future__ import annotations

import asyncio
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from gamification.domain.badge_rule import (
    FIRST_CONVERSATION_COMPLETED,
    FIRST_LEVEL_ADVANCED,
    STREAK_7_DAYS,
)
from gamification.infrastructure.models import Badge

_CATALOG: list[dict[str, str]] = [
    {
        "code": FIRST_CONVERSATION_COMPLETED,
        "name": "First Conversation",
        "description": "Completed your first learning-loop conversation turn.",
        "criteria_description": "Awarded on the first scored conversation turn.",
    },
    {
        "code": STREAK_7_DAYS,
        "name": "7-Day Streak",
        "description": "Practiced for 7 days in a row.",
        "criteria_description": "Awarded when streak_current reaches 7.",
    },
    {
        "code": FIRST_LEVEL_ADVANCED,
        "name": "Level Up!",
        "description": "Advanced to the next CEFR level for the first time.",
        "criteria_description": "Awarded on the student's first-ever level advancement.",
    },
]


async def seed(session: AsyncSession) -> None:
    for entry in _CATALOG:
        existing = await session.scalar(select(Badge.id).where(Badge.code == entry["code"]))
        if existing is not None:
            continue
        session.add(Badge(id=uuid.uuid4(), **entry))
    await session.commit()


async def _main() -> None:
    from shared_kernel.infrastructure.db import get_session_factory

    session_factory = get_session_factory()
    async with session_factory() as session:
        await seed(session)


if __name__ == "__main__":
    asyncio.run(_main())
