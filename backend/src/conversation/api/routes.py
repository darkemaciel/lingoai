"""Conversation API routes (T054) — contracts/rest-api.md "Learning Loop
(Conversation + Exercises)" section: `POST /api/v1/conversations`,
`POST /api/v1/conversations/{id}/messages`.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from conversation.application import conversation_service
from conversation.application.conversation_service import ConversationSessionNotFoundError
from identity.api.dependencies import get_current_user_id
from shared_kernel.infrastructure.db import get_db_session

router = APIRouter(prefix="/api/v1/conversations", tags=["conversations"])


class StartConversationResponse(BaseModel):
    conversation_session_id: str


class SendMessageRequest(BaseModel):
    client_submission_id: uuid.UUID
    content_text: str
    audio_ref: str | None = None


class AgentMessageResponse(BaseModel):
    content_text: str
    audio_ref: str | None = None


class GamificationDeltaResponse(BaseModel):
    xp_awarded: int
    xp_total: int
    streak_current: int
    badges_unlocked: list[str]


class SendMessageResponse(BaseModel):
    agent_message: AgentMessageResponse
    gamification_delta: GamificationDeltaResponse | None = None


@router.post("", response_model=StartConversationResponse, status_code=status.HTTP_201_CREATED)
async def start_conversation(
    user_id: uuid.UUID = Depends(get_current_user_id),
    session_db: AsyncSession = Depends(get_db_session),
) -> StartConversationResponse:
    session = await conversation_service.start_or_resume_session(session_db, user_id)
    return StartConversationResponse(conversation_session_id=str(session.id))


@router.post("/{conversation_id}/messages", response_model=SendMessageResponse)
async def send_message(
    conversation_id: uuid.UUID,
    request: SendMessageRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    session_db: AsyncSession = Depends(get_db_session),
) -> SendMessageResponse:
    try:
        result = await conversation_service.send_message(
            session_db,
            conversation_session_id=conversation_id,
            user_id=user_id,
            client_submission_id=request.client_submission_id,
            content_text=request.content_text,
            audio_ref=request.audio_ref,
        )
    except ConversationSessionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="conversation session not found"
        ) from exc

    return SendMessageResponse(
        agent_message=AgentMessageResponse(
            content_text=result.reply_text, audio_ref=result.reply_audio_ref
        ),
        gamification_delta=(
            GamificationDeltaResponse(
                xp_awarded=result.gamification_delta.xp_awarded,
                xp_total=result.gamification_delta.xp_total,
                streak_current=result.gamification_delta.streak_current,
                badges_unlocked=result.gamification_delta.badges_unlocked,
            )
            if result.gamification_delta is not None
            else None
        ),
    )
