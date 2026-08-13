"""SQLAlchemy models for the ``learning_content`` module (T043):
``LearningPath`` / ``Unit`` / ``Activity`` — the shared read model consumed
by ``conversation`` and ``progression`` (data-model.md, plan.md §8).

Like ``progression``/``gamification``, this module has no separate
framework-free domain entity — the SQLAlchemy model doubles as the entity,
since these are simple read-model records with no behavior beyond field
validation (data-model.md's "Validation" note on `Activity.type` is enforced
by the seed data / content-authoring process, not runtime domain logic).
Migration: backend/migrations/versions/0008_create_learning_content_tables.py.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from shared_kernel.domain.enums import ActivityType, CEFRLevel, Skill
from shared_kernel.infrastructure.db import Base


class LearningPath(Base):
    __tablename__ = "learning_paths"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    skill: Mapped[Skill] = mapped_column(
        Enum(
            Skill,
            name="skill",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
            create_type=False,
        ),
        nullable=False,
    )
    cefr_level: Mapped[CEFRLevel] = mapped_column(
        Enum(
            CEFRLevel,
            name="cefr_level",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
            create_type=False,
        ),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)


class Unit(Base):
    __tablename__ = "units"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    learning_path_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("learning_paths.id"), nullable=False, index=True
    )
    sequence_order: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)


class Activity(Base):
    __tablename__ = "activities"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    unit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("units.id"), nullable=False, index=True
    )
    type: Mapped[ActivityType] = mapped_column(
        Enum(
            ActivityType,
            name="activity_type",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    # Agent-consumable prompt/rubric definition (shape varies by `type`).
    prompt_content: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # Maps roughly to target mastery_score band (FR-7 activity selection).
    difficulty_hint: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
