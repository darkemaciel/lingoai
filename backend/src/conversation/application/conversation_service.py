"""Conversation application service (T052): send a message ->
`ConversationAgentPort` -> (if `scored`) `LearningEvent` -> progression +
gamification updates. Backs `POST /api/v1/conversations` and
`POST /api/v1/conversations/{id}/messages`.

Idempotency: keyed on (`user_id`, `client_submission_id`) via the shared
`LearningEvent` recorder (T050) — a retried/duplicate submission for a
*scored* turn returns the already-recorded agent reply without
re-invoking the agent or double-counting progression/gamification. Turns
where `scored=False` don't produce a `LearningEvent` at all (per the
agent-ports.md contract), so idempotency doesn't apply to them — a
duplicate non-scored submission is simply reprocessed, which has no
progression/gamification side effect to double-count.

**Audio note** (T069): mirrors `placement_service.py` — `audio_ref` on the
request transcribes to `audio_transcript` when `NullAudioAdapter` reports
it available (never, this iteration), and the agent's `reply_text` is
offered to `synthesize` for an outgoing `audio_ref`, same graceful
fallback (FR-14, AC-7).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_agents.adapter_factory import current_agent_provider, get_agent_adapter
from ai_agents.adapters.null_audio_adapter import NullAudioAdapter
from ai_agents.observability.agent_invocation_log import AgentName, log_agent_invocation
from ai_agents.ports.assessment_agent_port import ConversationTurnMessage
from ai_agents.ports.conversation_agent_port import (
    ConversationTurnInput,
    LearnerContext,
    LearnerSkillSnapshot,
)
from conversation.infrastructure.models import (
    ConversationSession,
    ConversationSessionStatus,
    Message,
    MessageSender,
)
from gamification.application.gamification_service import GamificationDelta
from gamification.application.gamification_service import (
    apply_scored_outcome as apply_gamification_outcome,
)
from identity.infrastructure.models import User
from progression.application.level_advancement_service import (
    apply_scored_outcome as apply_progression_outcome,
)
from progression.infrastructure.models import LearnerSkillProfile
from shared_kernel.application.learning_event_recorder import record_learning_event
from shared_kernel.domain.enums import ActivityType, Skill
from shared_kernel.infrastructure.learning_event_model import LearningEvent, LearningEventType

# Single shared instance — NullAudioAdapter is stateless (T015), and is the
# only bound audio implementation this iteration (research.md §2, T069).
_audio_adapter = NullAudioAdapter()


class ConversationSessionNotFoundError(Exception):
    pass


@dataclass(frozen=True)
class SendMessageResult:
    reply_text: str
    reply_audio_ref: str | None
    gamification_delta: GamificationDelta | None


async def start_or_resume_session(
    session_db: AsyncSession, user_id: uuid.UUID
) -> ConversationSession:
    """Returns the student's currently `active` `ConversationSession` if
    one exists (FR-6: "resumes the active" session), otherwise starts a
    new one."""
    existing = await session_db.scalar(
        select(ConversationSession).where(
            ConversationSession.user_id == user_id,
            ConversationSession.status == ConversationSessionStatus.ACTIVE,
        )
    )
    if existing is not None:
        return existing

    session = ConversationSession(id=uuid.uuid4(), user_id=user_id)
    session_db.add(session)
    await session_db.commit()
    return session


async def _history(
    session_db: AsyncSession, conversation_session_id: uuid.UUID
) -> list[ConversationTurnMessage]:
    rows = (
        (
            await session_db.execute(
                select(Message)
                .where(Message.conversation_session_id == conversation_session_id)
                .order_by(Message.created_at)
            )
        )
        .scalars()
        .all()
    )
    return [
        ConversationTurnMessage(
            sender="student" if row.sender == MessageSender.STUDENT else "agent",
            text=row.content_text,
        )
        for row in rows
    ]


async def _learner_context(session_db: AsyncSession, user_id: uuid.UUID) -> LearnerContext:
    rows = (
        (
            await session_db.execute(
                select(LearnerSkillProfile).where(LearnerSkillProfile.user_id == user_id)
            )
        )
        .scalars()
        .all()
    )
    return LearnerContext(
        skills=[
            LearnerSkillSnapshot(
                skill=str(row.skill),
                cefr_level=str(row.cefr_level),
                mastery_score=row.mastery_score,
            )
            for row in rows
        ]
    )


async def _is_first_scored_conversation_turn(session_db: AsyncSession, user_id: uuid.UUID) -> bool:
    existing = await session_db.scalar(
        select(LearningEvent.id)
        .where(
            LearningEvent.user_id == user_id,
            LearningEvent.event_type == LearningEventType.CONVERSATION_TURN_COMPLETED,
        )
        .limit(1)
    )
    return existing is None


async def send_message(
    session_db: AsyncSession,
    *,
    conversation_session_id: uuid.UUID,
    user_id: uuid.UUID,
    client_submission_id: uuid.UUID,
    content_text: str,
    audio_ref: str | None = None,
) -> SendMessageResult:
    conversation = await session_db.get(ConversationSession, conversation_session_id)
    if conversation is None or conversation.user_id != user_id:
        raise ConversationSessionNotFoundError(str(conversation_session_id))

    # Idempotency (spec Edge Case: duplicate submission) — only scored
    # turns ever record a LearningEvent, see module docstring.
    existing_event = await session_db.scalar(
        select(LearningEvent).where(
            LearningEvent.user_id == user_id,
            LearningEvent.client_submission_id == client_submission_id,
        )
    )
    if existing_event is not None:
        return SendMessageResult(
            reply_text=existing_event.payload.get("agent_reply_text", ""),
            reply_audio_ref=None,
            gamification_delta=None,
        )

    history = await _history(session_db, conversation_session_id)
    learner_context = await _learner_context(session_db, user_id)

    audio_transcript: str | None = None
    if audio_ref is not None:
        transcription = await _audio_adapter.transcribe(audio_ref)
        if transcription.available:
            audio_transcript = transcription.value

    session_db.add(
        Message(
            id=uuid.uuid4(),
            conversation_session_id=conversation_session_id,
            sender=MessageSender.STUDENT,
            content_text=content_text,
            audio_ref=audio_ref,
        )
    )

    async with log_agent_invocation(
        AgentName.CONVERSATION_AGENT,
        current_agent_provider(),
        input_summary=f"conversation turn for session {conversation_session_id}",
        session=session_db,
    ) as invocation:
        output = await get_agent_adapter().process_message(
            ConversationTurnInput(
                conversation_history=history,
                student_message=content_text,
                audio_transcript=audio_transcript,
                learner_context=learner_context,
            )
        )
        invocation.output_summary = f"scored={output.scored}"

    reply_audio_ref: str | None = None
    synthesis = await _audio_adapter.synthesize(output.reply_text)
    if synthesis.available:
        reply_audio_ref = synthesis.value

    session_db.add(
        Message(
            id=uuid.uuid4(),
            conversation_session_id=conversation_session_id,
            sender=MessageSender.AGENT,
            content_text=output.reply_text,
        )
    )
    conversation.last_message_at = datetime.now(UTC)

    gamification_delta: GamificationDelta | None = None

    if output.scored and output.skill is not None and output.performance_score is not None:
        is_first_turn = await _is_first_scored_conversation_turn(session_db, user_id)
        skill = Skill(output.skill)
        _, created = await record_learning_event(
            session_db,
            user_id=user_id,
            event_type=LearningEventType.CONVERSATION_TURN_COMPLETED,
            client_submission_id=client_submission_id,
            skill=skill,
            conversation_session_id=conversation_session_id,
            payload={
                "raw_response": content_text,
                "agent_reply_text": output.reply_text,
                "performance_score": output.performance_score,
                "feedback_text": output.feedback_text,
            },
        )
        if created:
            now = datetime.now(UTC)
            progression_outcome = await apply_progression_outcome(
                session_db,
                user_id=user_id,
                skill=skill,
                performance_score=output.performance_score,
                at=now,
            )
            user = await session_db.get(User, user_id)
            gamification_delta = await apply_gamification_outcome(
                session_db,
                user_id=user_id,
                activity_type=ActivityType.CONVERSATION_PROMPT,
                performance_score=output.performance_score,
                at=now,
                user_timezone=user.timezone if user is not None and user.timezone else "UTC",
                is_first_conversation_turn=is_first_turn,
                is_first_level_advancement=progression_outcome.is_first_level_advancement,
            )

    await session_db.commit()
    return SendMessageResult(
        reply_text=output.reply_text,
        reply_audio_ref=reply_audio_ref,
        gamification_delta=gamification_delta,
    )
