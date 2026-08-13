"""SQLAlchemy model for ``LearnerSkillProfile`` — one row per (user, skill),
the persisted form of spec.md's ``LearnerProfile`` (data-model.md
"LearnerSkillProfile"). Migration:
backend/migrations/versions/0005_create_learner_skill_profiles_table.py.

Model/table only (T025). The level-advancement domain rule — ``cefr_level``
advancing when ``accuracy_window`` has >= 5 entries at >= 80% accuracy,
``mastery_score`` recompute, ``accuracy_window`` append/trim to max 10 — is
implemented later by T046 in
``progression/domain/level_advancement_rule.py``. Nothing here enforces
those rules; this module just stores the columns.

The bootstrap side effect described in data-model.md ("PlacementResult
creation seeds one LearnerSkillProfile row per non-null skill level, at
mastery_score=0") is implemented by T029 in the ``placement`` module's
application service, not here.

CEFR enum note (reconciled — was a known follow-up, now resolved): this
model originally defined its own local ``CEFRLevel`` while
``placement/domain/`` was still under concurrent construction (T023/T024).
Both landed on the identical Postgres enum type name (``cefr_level``) and
values (A1..C2) independently, so no migration changed — this model now
simply imports the shared ``CEFRLevel`` from ``shared_kernel.domain.enums``
(same module that already holds ``Skill``, for the same reason: one
Postgres enum type reused across ``placement.PlacementResult`` and this
table, not two divergent ones).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from shared_kernel.domain.enums import CEFRLevel, Skill
from shared_kernel.infrastructure.db import Base


class LearnerSkillProfile(Base):
    __tablename__ = "learner_skill_profiles"
    __table_args__ = (
        UniqueConstraint("user_id", "skill", name="uq_learner_skill_profiles_user_skill"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    skill: Mapped[Skill] = mapped_column(
        Enum(
            Skill,
            name="skill",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    cefr_level: Mapped[CEFRLevel] = mapped_column(
        Enum(
            CEFRLevel,
            name="cefr_level",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    # Progress within the current CEFR level; drives activity difficulty
    # selection (FR-7). Range 0-100 is enforced at the domain-rule layer
    # (T046), not by a DB CHECK constraint here.
    mastery_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Denormalized cache of the last 10 scored LearningEvents for this
    # skill: [{"correct": bool, "at": iso-timestamp}, ...]. NOT the source
    # of truth — LearningEvent is (data-model.md).
    accuracy_window: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
