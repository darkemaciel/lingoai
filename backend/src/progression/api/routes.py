"""Progression API routes — contracts/rest-api.md "Progression &
Gamification (read models)" section: `GET /api/v1/progression/profile`
(T031) and `GET /api/v1/progression/profile/{skill}/history` (T056) — the
concrete mechanism behind AC-4 ("reconstruir/justificar por que o
LearnerProfile está no nível atual"), backed directly by the `LearningEvent`
audit trail rather than any derived/cached explanation.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from identity.api.dependencies import get_current_user_id
from progression.infrastructure.models import LearnerSkillProfile
from shared_kernel.domain.enums import Skill
from shared_kernel.infrastructure.db import get_db_session
from shared_kernel.infrastructure.learning_event_model import LearningEvent

router = APIRouter(prefix="/api/v1/progression", tags=["progression"])

# Cross-cutting pagination defaults per contracts/rest-api.md.
_DEFAULT_PAGE_LIMIT = 20
_MAX_PAGE_LIMIT = 100


class SkillProfileResponse(BaseModel):
    skill: str
    cefr_level: str
    mastery_score: int


class ProgressionProfileResponse(BaseModel):
    skills: list[SkillProfileResponse]


class LearningEventResponse(BaseModel):
    id: str
    event_type: str
    skill: str | None
    performance_score: float | None
    created_at: str
    payload: dict


class ProgressionHistoryResponse(BaseModel):
    events: list[LearningEventResponse]
    next_cursor: str | None


@router.get("/profile", response_model=ProgressionProfileResponse)
async def get_profile(
    user_id: uuid.UUID = Depends(get_current_user_id),
    session_db: AsyncSession = Depends(get_db_session),
) -> ProgressionProfileResponse:
    rows = (
        (
            await session_db.execute(
                select(LearnerSkillProfile).where(LearnerSkillProfile.user_id == user_id)
            )
        )
        .scalars()
        .all()
    )
    return ProgressionProfileResponse(
        skills=[
            SkillProfileResponse(
                skill=str(row.skill),
                cefr_level=str(row.cefr_level),
                mastery_score=row.mastery_score,
            )
            for row in rows
        ]
    )


@router.get("/profile/{skill}/history", response_model=ProgressionHistoryResponse)
async def get_skill_history(
    skill: str,
    cursor: str | None = None,
    limit: int = _DEFAULT_PAGE_LIMIT,
    user_id: uuid.UUID = Depends(get_current_user_id),
    session_db: AsyncSession = Depends(get_db_session),
) -> ProgressionHistoryResponse:
    try:
        skill_enum = Skill(skill)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"invalid skill '{skill}'"
        ) from exc

    page_limit = max(1, min(limit, _MAX_PAGE_LIMIT))

    query = (
        select(LearningEvent)
        .where(LearningEvent.user_id == user_id, LearningEvent.skill == skill_enum)
        .order_by(LearningEvent.created_at.desc())
    )
    if cursor:
        try:
            cursor_at = datetime.fromisoformat(cursor)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid cursor"
            ) from exc
        query = query.where(LearningEvent.created_at < cursor_at)

    # Fetch one extra row to know whether a next page exists, without a
    # separate COUNT query.
    rows = (await session_db.execute(query.limit(page_limit + 1))).scalars().all()
    has_more = len(rows) > page_limit
    page = rows[:page_limit]

    return ProgressionHistoryResponse(
        events=[
            LearningEventResponse(
                id=str(row.id),
                event_type=str(row.event_type),
                skill=str(row.skill) if row.skill else None,
                performance_score=row.payload.get("performance_score"),
                created_at=row.created_at.isoformat(),
                payload=row.payload,
            )
            for row in page
        ],
        next_cursor=page[-1].created_at.isoformat() if has_more and page else None,
    )
