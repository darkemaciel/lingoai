"""Placement API routes — contracts/rest-api.md "Placement (Nivelamento)"
section: POST /api/v1/placement/sessions, POST .../answers,
GET .../result.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from identity.api.dependencies import get_current_user_id
from placement.application import placement_service
from placement.application.placement_service import (
    PlacementResultNotAvailableError,
    PlacementSessionAlreadyTerminalError,
    PlacementSessionNotFoundError,
)
from placement.domain.placement_session import PlacementModality
from shared_kernel.infrastructure.db import get_db_session

router = APIRouter(prefix="/api/v1/placement", tags=["placement"])


class StartSessionResponse(BaseModel):
    placement_session_id: str
    status: str
    modality: str


class SubmitAnswerRequest(BaseModel):
    client_submission_id: uuid.UUID
    content_text: str
    audio_ref: str | None = None


class NextPromptResponse(BaseModel):
    content_text: str
    audio_ref: str | None = None


class SubmitAnswerResponse(BaseModel):
    next_prompt: NextPromptResponse | None
    session_status: str


class PlacementResultResponse(BaseModel):
    reading_level: str
    writing_level: str
    speaking_level: str | None
    listening_level: str | None
    strengths_summary: str
    weaknesses_summary: str


async def _owned_session_or_404(
    session_db: AsyncSession, session_id: uuid.UUID, user_id: uuid.UUID
):
    """Load the session and enforce ownership, collapsing "not found" and
    "not owned" into the same 404 per contracts/rest-api.md (never leak
    whether a session id exists for a different user)."""
    try:
        entity = await placement_service.get_session(session_db, session_id)
    except PlacementSessionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="placement session not found"
        ) from exc
    if entity.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="placement session not found"
        )
    return entity


@router.post("/sessions", response_model=StartSessionResponse, status_code=status.HTTP_201_CREATED)
async def start_session(
    user_id: uuid.UUID = Depends(get_current_user_id),
    session_db: AsyncSession = Depends(get_db_session),
) -> StartSessionResponse:
    # Modality defaults to text_only at session start (FR-3); it reflects
    # whether audio was actually used, decided per-answer, not up front —
    # T069 (User Story 3) is what would let a client signal audio intent.
    entity = await placement_service.start_session(
        session_db, user_id=user_id, modality=PlacementModality.TEXT_ONLY
    )
    return StartSessionResponse(
        placement_session_id=str(entity.id),
        status=str(entity.status),
        modality=str(entity.modality),
    )


@router.post("/sessions/{session_id}/answers", response_model=SubmitAnswerResponse)
async def submit_answer(
    session_id: uuid.UUID,
    request: SubmitAnswerRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    session_db: AsyncSession = Depends(get_db_session),
) -> SubmitAnswerResponse:
    await _owned_session_or_404(session_db, session_id, user_id)
    try:
        result = await placement_service.submit_answer(
            session_db,
            session_id=session_id,
            user_id=user_id,
            client_submission_id=request.client_submission_id,
            content_text=request.content_text,
            audio_ref=request.audio_ref,
        )
    except PlacementSessionAlreadyTerminalError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="placement session already completed or abandoned",
        ) from exc
    return SubmitAnswerResponse(
        next_prompt=(
            NextPromptResponse(
                content_text=result.next_prompt.content_text,
                audio_ref=result.next_prompt.audio_ref,
            )
            if result.next_prompt is not None
            else None
        ),
        session_status=str(result.session_status),
    )


@router.get("/sessions/{session_id}/result", response_model=PlacementResultResponse)
async def get_result(
    session_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    session_db: AsyncSession = Depends(get_db_session),
) -> PlacementResultResponse:
    await _owned_session_or_404(session_db, session_id, user_id)
    try:
        result = await placement_service.get_result(session_db, session_id)
    except PlacementResultNotAvailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="placement session not completed yet",
        ) from exc
    return PlacementResultResponse(
        reading_level=str(result.reading_level),
        writing_level=str(result.writing_level),
        speaking_level=str(result.speaking_level) if result.speaking_level else None,
        listening_level=str(result.listening_level) if result.listening_level else None,
        strengths_summary=result.strengths_summary,
        weaknesses_summary=result.weaknesses_summary,
    )
