"""Learning-content API routes (T055) — contracts/rest-api.md
`GET /api/v1/activities/next`, `POST /api/v1/activities/{id}/answers`.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from identity.api.dependencies import get_current_user_id
from learning_content.application import activity_answer_service
from learning_content.application.activity_answer_service import ActivityNotFoundError
from progression.application.activity_selection_service import (
    NoActivityAvailableError,
    select_next_activity,
)
from shared_kernel.infrastructure.db import get_db_session

router = APIRouter(prefix="/api/v1/activities", tags=["activities"])


class NextActivityResponse(BaseModel):
    activity_id: str
    type: str
    skill: str
    prompt_content: dict


class SubmitActivityAnswerRequest(BaseModel):
    client_submission_id: uuid.UUID
    response: dict


class GamificationDeltaResponse(BaseModel):
    xp_awarded: int
    xp_total: int
    streak_current: int
    badges_unlocked: list[str]


class ActivityAnswerResponse(BaseModel):
    correct: bool
    feedback_text: str
    performance_score: float
    gamification_delta: GamificationDeltaResponse
    level_advanced: bool


@router.get("/next", response_model=NextActivityResponse)
async def get_next_activity(
    user_id: uuid.UUID = Depends(get_current_user_id),
    session_db: AsyncSession = Depends(get_db_session),
) -> NextActivityResponse:
    try:
        next_activity = await select_next_activity(session_db, user_id)
    except NoActivityAvailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="no activity available"
        ) from exc

    return NextActivityResponse(
        activity_id=str(next_activity.activity_id),
        type=str(next_activity.type),
        skill=str(next_activity.skill),
        prompt_content=next_activity.prompt_content,
    )


@router.post("/{activity_id}/answers", response_model=ActivityAnswerResponse)
async def submit_activity_answer(
    activity_id: uuid.UUID,
    request: SubmitActivityAnswerRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    session_db: AsyncSession = Depends(get_db_session),
) -> ActivityAnswerResponse:
    try:
        result = await activity_answer_service.submit_answer(
            session_db,
            activity_id=activity_id,
            user_id=user_id,
            client_submission_id=request.client_submission_id,
            response=request.response,
        )
    except ActivityNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="activity not found"
        ) from exc

    return ActivityAnswerResponse(
        correct=result.correct,
        feedback_text=result.feedback_text,
        performance_score=result.performance_score,
        gamification_delta=GamificationDeltaResponse(
            xp_awarded=result.gamification_delta.xp_awarded,
            xp_total=result.gamification_delta.xp_total,
            streak_current=result.gamification_delta.streak_current,
            badges_unlocked=result.gamification_delta.badges_unlocked,
        ),
        level_advanced=result.level_advanced,
    )
