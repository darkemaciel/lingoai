"""Learning-content application service (T053): submit an answer to an
exercise Activity -> `ProgressionSignalAgentPort` judges the open-ended
response -> `LearningEvent` -> progression + gamification + badge updates
-> feedback response. Backs `POST /api/v1/activities/{id}/answers`.

All seeded Activity types this iteration (writing/speaking/listening
exercise) are open-ended, so every answer goes through
`ProgressionSignalAgentPort` — there is no multiple-choice/exact-match
Activity type in this slice's content model to skip it for (contracts/
agent-ports.md's "Multiple-choice/exact-match exercises skip this port
entirely" branch is simply unused by the current seed data, not a case
this service needs to special-case).

Idempotency: identical pattern to `conversation_service.py` — an early
duplicate check on (`user_id`, `client_submission_id`) short-circuits
before the agent is invoked or any progression/gamification update runs;
the shared `LearningEvent` recorder (T050) is still the final write.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_agents.adapter_factory import current_agent_provider, get_agent_adapter
from ai_agents.observability.agent_invocation_log import AgentName, log_agent_invocation
from ai_agents.ports.progression_signal_agent_port import ProgressionSignalInput
from gamification.application.gamification_service import GamificationDelta
from gamification.application.gamification_service import (
    apply_scored_outcome as apply_gamification_outcome,
)
from identity.infrastructure.models import User
from learning_content.infrastructure.models import Activity, LearningPath, Unit
from progression.application.level_advancement_service import (
    apply_scored_outcome as apply_progression_outcome,
)
from progression.domain.level_advancement_rule import performance_score_is_correct
from shared_kernel.application.learning_event_recorder import record_learning_event
from shared_kernel.domain.enums import ActivityType
from shared_kernel.infrastructure.learning_event_model import LearningEvent, LearningEventType


class ActivityNotFoundError(Exception):
    pass


@dataclass(frozen=True)
class ActivityAnswerResult:
    correct: bool
    feedback_text: str
    performance_score: float
    gamification_delta: GamificationDelta
    level_advanced: bool


def _extract_student_response_text(response: dict) -> str:
    """`response`'s shape "depends on activity type" per contracts/
    rest-api.md; every seeded exercise type this iteration is free-text, so
    a `"text"` field is expected. Falls back to a JSON-ish string of the
    whole payload if absent, rather than raising, so an unexpected shape
    still gets *some* judged response instead of a hard 500."""
    text = response.get("text")
    return text if isinstance(text, str) else str(response)


async def submit_answer(
    session_db: AsyncSession,
    *,
    activity_id: uuid.UUID,
    user_id: uuid.UUID,
    client_submission_id: uuid.UUID,
    response: dict,
) -> ActivityAnswerResult:
    activity = await session_db.get(Activity, activity_id)
    if activity is None:
        raise ActivityNotFoundError(str(activity_id))

    # The skill this Activity belongs to is derived from its content-model
    # placement (Activity -> Unit -> LearningPath.skill), never taken from
    # client input — the caller submits an answer, not a skill claim.
    skill = await session_db.scalar(
        select(LearningPath.skill)
        .join(Unit, Unit.learning_path_id == LearningPath.id)
        .where(Unit.id == activity.unit_id)
    )
    if skill is None:
        raise ActivityNotFoundError(str(activity_id))

    existing_event = await session_db.scalar(
        select(LearningEvent).where(
            LearningEvent.user_id == user_id,
            LearningEvent.client_submission_id == client_submission_id,
        )
    )
    if existing_event is not None:
        payload = existing_event.payload
        return ActivityAnswerResult(
            correct=payload.get("correct", False),
            feedback_text=payload.get("feedback_text", ""),
            performance_score=payload.get("performance_score", 0.0),
            gamification_delta=GamificationDelta(
                xp_awarded=0,
                xp_total=payload.get("xp_total", 0),
                streak_current=payload.get("streak_current", 0),
                badges_unlocked=[],
            ),
            level_advanced=False,
        )

    student_response_text = _extract_student_response_text(response)

    async with log_agent_invocation(
        AgentName.PROGRESSION_AGENT,
        current_agent_provider(),
        input_summary=f"activity answer for activity {activity_id}",
        session=session_db,
    ) as invocation:
        signal = await get_agent_adapter().evaluate(
            ProgressionSignalInput(
                activity_prompt=str(activity.prompt_content.get("instructions", "")),
                student_response=student_response_text,
                rubric=activity.prompt_content.get("rubric", {}),
            )
        )
        invocation.output_summary = f"performance_score={signal.performance_score:.2f}"

    correct = performance_score_is_correct(signal.performance_score)
    now = datetime.now(UTC)

    progression_outcome = await apply_progression_outcome(
        session_db,
        user_id=user_id,
        skill=skill,
        performance_score=signal.performance_score,
        at=now,
    )
    user = await session_db.get(User, user_id)
    gamification_delta = await apply_gamification_outcome(
        session_db,
        user_id=user_id,
        activity_type=ActivityType(activity.type),
        performance_score=signal.performance_score,
        at=now,
        user_timezone=user.timezone if user is not None else "UTC",
        is_first_level_advancement=progression_outcome.is_first_level_advancement,
    )

    await record_learning_event(
        session_db,
        user_id=user_id,
        event_type=LearningEventType.EXERCISE_ANSWER_SUBMITTED,
        client_submission_id=client_submission_id,
        skill=skill,
        activity_id=activity_id,
        payload={
            "raw_response": student_response_text,
            "correct": correct,
            "performance_score": signal.performance_score,
            "feedback_text": signal.feedback_text,
            "xp_total": gamification_delta.xp_total,
            "streak_current": gamification_delta.streak_current,
        },
    )

    await session_db.commit()

    return ActivityAnswerResult(
        correct=correct,
        feedback_text=signal.feedback_text,
        performance_score=signal.performance_score,
        gamification_delta=gamification_delta,
        level_advanced=progression_outcome.level_advanced,
    )
