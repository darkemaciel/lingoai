"""Shared `LearningEvent` recorder (T050) — idempotent create on
(`user_id`, `client_submission_id`), per data-model.md's idempotency rule
(spec Edge Case: rapid double-send / duplicate submission).

Generalizes the check-then-insert logic `placement/application/
placement_service.py` (T028) hand-rolled before this task existed; new
modules (`conversation`, `learning_content`) call this instead of
duplicating it. `placement_service.py` itself is left as-is per its own
docstring note (documented follow-up, not required for this slice).
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared_kernel.domain.enums import Skill
from shared_kernel.infrastructure.learning_event_model import LearningEvent, LearningEventType


async def record_learning_event(
    session_db: AsyncSession,
    *,
    user_id: uuid.UUID,
    event_type: LearningEventType,
    client_submission_id: uuid.UUID,
    payload: dict,
    skill: Skill | None = None,
    activity_id: uuid.UUID | None = None,
    placement_session_id: uuid.UUID | None = None,
    conversation_session_id: uuid.UUID | None = None,
) -> tuple[LearningEvent, bool]:
    """Returns `(event, created)`. If an event already exists for this
    `(user_id, client_submission_id)` pair, it is returned unchanged
    (`created=False`) instead of inserting a duplicate — callers use
    `created` to decide whether to also apply the event's downstream
    side effects (progression/gamification updates), which must never run
    twice for the same client submission.

    Does not commit — the caller controls the transaction boundary, so this
    can participate in a larger unit of work alongside progression/
    gamification updates triggered by the same event.
    """
    existing = await session_db.scalar(
        select(LearningEvent).where(
            LearningEvent.user_id == user_id,
            LearningEvent.client_submission_id == client_submission_id,
        )
    )
    if existing is not None:
        return existing, False

    event = LearningEvent(
        id=uuid.uuid4(),
        user_id=user_id,
        event_type=event_type,
        skill=skill,
        activity_id=activity_id,
        placement_session_id=placement_session_id,
        conversation_session_id=conversation_session_id,
        client_submission_id=client_submission_id,
        payload=payload,
    )
    session_db.add(event)
    await session_db.flush()
    return event, True
