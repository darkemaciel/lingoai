"""Placement application service — start/answer/complete a placement
session, calling ``AssessmentAgentPort`` for each turn, and (T029) bootstrap
``LearnerSkillProfile``/``GamificationProfile`` rows once the session
completes. Request/response shapes are fixed by contracts/rest-api.md's
"Placement" section; kept separate from FastAPI (placement/api/routes.py)
so the logic is testable without an HTTP layer.

**Idempotency note**: this module hand-rolls a minimal idempotent
`LearningEvent` insert (check-then-insert on the (user_id,
client_submission_id) unique constraint) so AC-2's "duplicate submission"
edge case holds for placement answers *now*. T050 (User Story 2) introduces
a shared, generalized `LearningEvent` recorder used by every module —
once that lands, this module's insert path should be migrated to call it
instead of duplicating the logic.

**Audio note** (T069): `SpeechToTextProvider.transcribe`/`TextToSpeechProvider
.synthesize` are called here — via `NullAudioAdapter`, the only bound
implementation this iteration (research.md §2) — so the ports are
demonstrably wired end-to-end (AC-7) even though every call currently
reports "not available" and the flow gracefully falls back to text-only
(FR-14). `audio_ref` on the request transcribes to `audio_transcript` when
available; the agent's `next_prompt_text` is offered to `synthesize` for an
outgoing `audio_ref`, again only when available.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_agents.adapter_factory import current_agent_provider, get_agent_adapter
from ai_agents.adapters.null_audio_adapter import NullAudioAdapter
from ai_agents.observability.agent_invocation_log import AgentName, log_agent_invocation
from ai_agents.ports.assessment_agent_port import (
    AssessmentTurnInput,
    ConversationTurnMessage,
    SkillSignal,
    SkillSignals,
)
from gamification.infrastructure.models import GamificationProfile
from placement.domain.placement_result import PlacementResult
from placement.domain.placement_session import (
    PlacementModality,
    PlacementSession,
    PlacementSessionStatus,
)
from placement.infrastructure.models import (
    PlacementResultModel,
    PlacementSessionModel,
    apply_session_state,
    result_to_domain,
    result_to_row,
    session_to_domain,
    session_to_row,
)
from progression.infrastructure.models import LearnerSkillProfile
from shared_kernel.domain.enums import CEFRLevel, Skill
from shared_kernel.infrastructure.learning_event_model import LearningEvent, LearningEventType


class PlacementSessionNotFoundError(Exception):
    pass


class PlacementSessionAlreadyTerminalError(Exception):
    pass


class PlacementResultNotAvailableError(Exception):
    """Raised by `get_result` when the session has no result yet (not
    completed) — maps to the `409 session not completed yet` response in
    contracts/rest-api.md."""


@dataclass
class NextPrompt:
    content_text: str
    audio_ref: str | None = None


@dataclass
class SubmitAnswerResult:
    next_prompt: NextPrompt | None
    session_status: PlacementSessionStatus


# Single shared instance — NullAudioAdapter is stateless (T015), and is the
# only bound audio implementation this iteration (research.md §2).
_audio_adapter = NullAudioAdapter()


async def start_session(
    session_db: AsyncSession, user_id: uuid.UUID, modality: PlacementModality
) -> PlacementSession:
    entity = PlacementSession.start(user_id=user_id, modality=modality)
    session_db.add(session_to_row(entity))
    await session_db.commit()
    return entity


async def _load_session(session_db: AsyncSession, session_id: uuid.UUID) -> PlacementSessionModel:
    row = await session_db.get(PlacementSessionModel, session_id)
    if row is None:
        raise PlacementSessionNotFoundError(str(session_id))
    return row


async def _conversation_so_far(
    session_db: AsyncSession, placement_session_id: uuid.UUID
) -> list[ConversationTurnMessage]:
    """Reconstruct the transcript from prior `LearningEvent` rows for this
    session, ordered by `created_at`. Each turn's payload holds both the
    student's `raw_response` and the agent's `agent_prompt` that followed
    it, so a stored event round-trips into (student, agent) message pairs.
    """
    rows = (
        (
            await session_db.execute(
                select(LearningEvent)
                .where(
                    LearningEvent.placement_session_id == placement_session_id,
                    LearningEvent.event_type == LearningEventType.PLACEMENT_ANSWER_SUBMITTED,
                )
                .order_by(LearningEvent.created_at)
            )
        )
        .scalars()
        .all()
    )
    messages: list[ConversationTurnMessage] = []
    for row in rows:
        messages.append(ConversationTurnMessage(sender="student", text=row.payload["raw_response"]))
        agent_prompt = row.payload.get("agent_prompt")
        if agent_prompt:
            messages.append(ConversationTurnMessage(sender="agent", text=agent_prompt))
    return messages


async def submit_answer(
    session_db: AsyncSession,
    *,
    session_id: uuid.UUID,
    user_id: uuid.UUID,
    client_submission_id: uuid.UUID,
    content_text: str,
    audio_ref: str | None = None,
) -> SubmitAnswerResult:
    row = await _load_session(session_db, session_id)
    entity = session_to_domain(row)
    if entity.is_terminal:
        raise PlacementSessionAlreadyTerminalError(str(session_id))

    # Idempotency: a duplicate client_submission_id returns the session's
    # current state without re-invoking the agent or double-recording an
    # event (spec Edge Case: rapid double-send).
    existing = await session_db.scalar(
        select(LearningEvent).where(
            LearningEvent.user_id == user_id,
            LearningEvent.client_submission_id == client_submission_id,
        )
    )
    if existing is not None:
        return SubmitAnswerResult(
            next_prompt=(
                NextPrompt(content_text=existing.payload["agent_prompt"])
                if existing.payload.get("agent_prompt")
                else None
            ),
            session_status=entity.status,
        )

    conversation_so_far = await _conversation_so_far(session_db, session_id)

    audio_transcript: str | None = None
    if audio_ref is not None:
        transcription = await _audio_adapter.transcribe(audio_ref)
        if transcription.available:
            audio_transcript = transcription.value

    turn_number = len(conversation_so_far) // 2 + 1
    async with log_agent_invocation(
        AgentName.ASSESSMENT_AGENT,
        current_agent_provider(),
        input_summary=f"placement turn {turn_number} for session {session_id}",
        session=session_db,
    ) as invocation:
        output = await get_agent_adapter().process_turn(
            AssessmentTurnInput(
                conversation_so_far=conversation_so_far,
                latest_student_response=content_text,
                audio_transcript=audio_transcript,
            )
        )
        invocation.output_summary = (
            "complete" if output.is_complete else f"next_prompt={output.next_prompt_text!r}"
        )

    next_prompt_audio_ref: str | None = None
    if output.next_prompt_text is not None:
        synthesis = await _audio_adapter.synthesize(output.next_prompt_text)
        if synthesis.available:
            next_prompt_audio_ref = synthesis.value

    session_db.add(
        LearningEvent(
            id=uuid.uuid4(),
            user_id=user_id,
            event_type=LearningEventType.PLACEMENT_ANSWER_SUBMITTED,
            skill=None,
            placement_session_id=session_id,
            client_submission_id=client_submission_id,
            payload={
                "raw_response": content_text,
                "agent_prompt": output.next_prompt_text,
                "audio_ref": audio_ref,
            },
        )
    )

    if output.is_complete:
        entity.complete()
        apply_session_state(row, entity)
        await _complete_session(
            session_db,
            entity,
            skill_signals=output.skill_signals or SkillSignals(),
            strengths_summary=output.strengths_summary or "",
            weaknesses_summary=output.weaknesses_summary or "",
        )
        await session_db.commit()
        return SubmitAnswerResult(next_prompt=None, session_status=entity.status)

    await session_db.commit()
    return SubmitAnswerResult(
        next_prompt=NextPrompt(
            content_text=output.next_prompt_text or "", audio_ref=next_prompt_audio_ref
        ),
        session_status=entity.status,
    )


async def _complete_session(
    session_db: AsyncSession,
    entity: PlacementSession,
    *,
    skill_signals: SkillSignals,
    strengths_summary: str,
    weaknesses_summary: str,
) -> PlacementResult:
    """T028's `complete_session` step, extended by T029: persists the
    `PlacementResult` and bootstraps the `LearnerSkillProfile`/
    `GamificationProfile` rows it seeds, all in the caller's transaction
    (committed by `submit_answer`)."""
    result = PlacementResult.from_completed_session(
        entity,
        reading_level=skill_signal_to_cefr_level(skill_signals.reading),
        writing_level=skill_signal_to_cefr_level(skill_signals.writing),
        speaking_level=skill_signal_to_cefr_level(skill_signals.speaking),
        listening_level=skill_signal_to_cefr_level(skill_signals.listening),
        strengths_summary=strengths_summary,
        weaknesses_summary=weaknesses_summary,
    )
    session_db.add(result_to_row(result))

    await _bootstrap_learner_skill_profiles(session_db, entity.user_id, result)
    await _bootstrap_gamification_profile(session_db, entity.user_id)

    return result


def skill_signal_to_cefr_level(signal: SkillSignal | None) -> CEFRLevel | None:
    """Pure derivation: one `AssessmentTurnOutput.skill_signals` entry ->
    the `CEFRLevel` persisted onto `PlacementResult`. `None` in, `None`
    out (no audio modality used for that skill, FR-3) — otherwise the
    signal's `cefr_level` string is parsed into the enum. Exposed
    (not `_`-prefixed) so it's directly unit-testable (T019) without a DB
    session, separate from the DB-touching bootstrap side effects below."""
    return CEFRLevel(signal.cefr_level) if signal is not None else None


_RESULT_SKILL_FIELDS: list[tuple[str, Skill]] = [
    ("reading_level", Skill.READING),
    ("writing_level", Skill.WRITING),
    ("speaking_level", Skill.SPEAKING),
    ("listening_level", Skill.LISTENING),
]


async def _bootstrap_learner_skill_profiles(
    session_db: AsyncSession, user_id: uuid.UUID, result: PlacementResult
) -> None:
    """One `LearnerSkillProfile` row per non-null skill level on `result`,
    at `mastery_score=0` (data-model.md's PlacementResult "Side effect").
    Skipped per-skill if a row already exists (unique on user_id+skill) —
    defensive idempotency in case this ever runs twice for the same user."""
    for field_name, skill in _RESULT_SKILL_FIELDS:
        level: CEFRLevel | None = getattr(result, field_name)
        if level is None:
            continue
        already_exists = await session_db.scalar(
            select(LearnerSkillProfile.id).where(
                LearnerSkillProfile.user_id == user_id, LearnerSkillProfile.skill == skill
            )
        )
        if already_exists is not None:
            continue
        session_db.add(
            LearnerSkillProfile(
                id=uuid.uuid4(),
                user_id=user_id,
                skill=skill,
                cefr_level=level,
                mastery_score=0,
                accuracy_window=[],
            )
        )


async def _bootstrap_gamification_profile(session_db: AsyncSession, user_id: uuid.UUID) -> None:
    already_exists = await session_db.scalar(
        select(GamificationProfile.id).where(GamificationProfile.user_id == user_id)
    )
    if already_exists is not None:
        return
    session_db.add(
        GamificationProfile(
            id=uuid.uuid4(),
            user_id=user_id,
            xp_total=0,
            streak_current=0,
            streak_last_activity_date=None,
        )
    )


async def get_result(session_db: AsyncSession, session_id: uuid.UUID) -> PlacementResult:
    row = await session_db.scalar(
        select(PlacementResultModel).where(PlacementResultModel.placement_session_id == session_id)
    )
    if row is None:
        raise PlacementResultNotAvailableError(str(session_id))
    return result_to_domain(row)


async def get_session(session_db: AsyncSession, session_id: uuid.UUID) -> PlacementSession:
    row = await _load_session(session_db, session_id)
    return session_to_domain(row)
