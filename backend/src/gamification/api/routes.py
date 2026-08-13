"""Gamification API routes (T057) — contracts/rest-api.md
`GET /api/v1/gamification/profile`, the persistent progress panel
(FR-19, SC-007)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from gamification.infrastructure.models import Badge, BadgeAward, GamificationProfile
from identity.api.dependencies import get_current_user_id
from shared_kernel.infrastructure.db import get_db_session

router = APIRouter(prefix="/api/v1/gamification", tags=["gamification"])


class BadgeResponse(BaseModel):
    code: str
    name: str
    description: str
    awarded_at: str


class GamificationProfileResponse(BaseModel):
    xp_total: int
    streak_current: int
    badges: list[BadgeResponse]


@router.get("/profile", response_model=GamificationProfileResponse)
async def get_profile(
    user_id: uuid.UUID = Depends(get_current_user_id),
    session_db: AsyncSession = Depends(get_db_session),
) -> GamificationProfileResponse:
    profile = await session_db.scalar(
        select(GamificationProfile).where(GamificationProfile.user_id == user_id)
    )
    if profile is None:
        return GamificationProfileResponse(xp_total=0, streak_current=0, badges=[])

    awards = (
        await session_db.execute(
            select(Badge, BadgeAward)
            .join(BadgeAward, BadgeAward.badge_id == Badge.id)
            .where(BadgeAward.user_id == user_id)
            .order_by(BadgeAward.awarded_at)
        )
    ).all()

    return GamificationProfileResponse(
        xp_total=profile.xp_total,
        streak_current=profile.streak_current,
        badges=[
            BadgeResponse(
                code=badge.code,
                name=badge.name,
                description=badge.description,
                awarded_at=award.awarded_at.isoformat(),
            )
            for badge, award in awards
        ],
    )
