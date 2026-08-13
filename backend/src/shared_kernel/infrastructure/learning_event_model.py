"""SQLAlchemy model for ``LearningEvent`` — the append-only event log that is
the single source of truth for learning progress (Constitution §12,
data-model.md).

APPEND-ONLY: application code MUST only INSERT rows into this table — never
UPDATE or DELETE. ``LearnerSkillProfile`` and ``GamificationProfile`` are
projections that are safely rebuildable by replaying this stream (Rollback
Considerations, spec.md). Do not add update/delete helper methods to this
model; if you find yourself wanting one, the design has gone wrong somewhere
upstream.

Idempotency: the unique constraint on (``user_id``, ``client_submission_id``)
is the dedup key for duplicate/retried client submissions (spec Edge Case:
rapid double-send). The shared ``LearningEvent`` recorder application service
(T050) upserts against it so downstream projections are never
double-counted.

``activity_id`` / ``placement_session_id`` / ``conversation_session_id`` are
plain nullable UUID columns with NO foreign-key constraint yet: the
``learning_content``, ``placement``, and ``conversation`` modules that own
those tables are introduced in later tasks (T027, T043, T044). FK
constraints referencing them can be added in a follow-up migration once
those tables exist — data-model.md documents the intended relationship even
though it isn't DB-enforced yet.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from shared_kernel.domain.enums import Skill
from shared_kernel.infrastructure.db import Base


class LearningEventType(enum.StrEnum):
    PLACEMENT_ANSWER_SUBMITTED = "placement_answer_submitted"
    EXERCISE_ANSWER_SUBMITTED = "exercise_answer_submitted"
    CONVERSATION_TURN_COMPLETED = "conversation_turn_completed"
    LEVEL_ADVANCED = "level_advanced"
    BADGE_AWARDED = "badge_awarded"


class LearningEvent(Base):
    __tablename__ = "learning_events"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "client_submission_id",
            name="uq_learning_events_user_client_submission",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    event_type: Mapped[LearningEventType] = mapped_column(
        Enum(
            LearningEventType,
            name="learning_event_type",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    skill: Mapped[Skill | None] = mapped_column(
        Enum(
            Skill,
            name="skill",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=True,
    )
    # Nullable, no FK — see module docstring.
    activity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    placement_session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    conversation_session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    client_submission_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    # {raw_response, performance_score: 0..1, feedback_text, time_spent_ms, attempt_number}
    # shape varies slightly by event_type (data-model.md).
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
