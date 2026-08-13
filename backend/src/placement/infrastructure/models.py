"""SQLAlchemy persistence models for the ``placement`` module, plus the
mapping functions between these ORM rows and the pure domain entities in
``placement.domain`` (T023/T024). Migration:
backend/migrations/versions/0007_create_placement_tables.py.

Unlike ``identity``/``progression``/``gamification`` (which use their
SQLAlchemy model directly as the "entity"), ``placement`` has real
framework-free domain entities (``PlacementSession``, ``PlacementResult``)
per Clean Architecture (Constitution §3) — so this module's job is strictly
translation: DB row <-> domain object. No business rules live here.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from placement.domain.placement_result import PlacementResult
from placement.domain.placement_session import (
    PlacementModality,
    PlacementSession,
    PlacementSessionStatus,
)
from shared_kernel.domain.enums import CEFRLevel
from shared_kernel.infrastructure.db import Base


class PlacementSessionModel(Base):
    __tablename__ = "placement_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    status: Mapped[PlacementSessionStatus] = mapped_column(
        Enum(
            PlacementSessionStatus,
            name="placement_session_status",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    modality: Mapped[PlacementModality] = mapped_column(
        Enum(
            PlacementModality,
            name="placement_modality",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PlacementResultModel(Base):
    __tablename__ = "placement_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    placement_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("placement_sessions.id"),
        nullable=False,
        unique=True,
    )
    reading_level: Mapped[CEFRLevel] = mapped_column(
        Enum(
            CEFRLevel,
            name="cefr_level",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
            create_type=False,
        ),
        nullable=False,
    )
    writing_level: Mapped[CEFRLevel] = mapped_column(
        Enum(
            CEFRLevel,
            name="cefr_level",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
            create_type=False,
        ),
        nullable=False,
    )
    speaking_level: Mapped[CEFRLevel | None] = mapped_column(
        Enum(
            CEFRLevel,
            name="cefr_level",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
            create_type=False,
        ),
        nullable=True,
    )
    listening_level: Mapped[CEFRLevel | None] = mapped_column(
        Enum(
            CEFRLevel,
            name="cefr_level",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
            create_type=False,
        ),
        nullable=True,
    )
    strengths_summary: Mapped[str] = mapped_column(Text, nullable=False)
    weaknesses_summary: Mapped[str] = mapped_column(Text, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


# ---------------------------------------------------------------------------
# Row <-> domain entity mapping
# ---------------------------------------------------------------------------


def session_to_domain(row: PlacementSessionModel) -> PlacementSession:
    return PlacementSession(
        id=row.id,
        user_id=row.user_id,
        status=row.status,
        modality=row.modality,
        started_at=row.started_at,
        completed_at=row.completed_at,
    )


def session_to_row(entity: PlacementSession) -> PlacementSessionModel:
    return PlacementSessionModel(
        id=entity.id,
        user_id=entity.user_id,
        status=entity.status,
        modality=entity.modality,
        started_at=entity.started_at,
        completed_at=entity.completed_at,
    )


def apply_session_state(row: PlacementSessionModel, entity: PlacementSession) -> None:
    """Copy mutable state from `entity` onto an already-persisted `row`
    (used after calling `entity.complete()`/`.abandon()`, before commit)."""
    row.status = entity.status
    row.completed_at = entity.completed_at


def result_to_domain(row: PlacementResultModel) -> PlacementResult:
    return PlacementResult(
        id=row.id,
        placement_session_id=row.placement_session_id,
        reading_level=row.reading_level,
        writing_level=row.writing_level,
        speaking_level=row.speaking_level,
        listening_level=row.listening_level,
        strengths_summary=row.strengths_summary,
        weaknesses_summary=row.weaknesses_summary,
        generated_at=row.generated_at,
    )


def result_to_row(entity: PlacementResult) -> PlacementResultModel:
    return PlacementResultModel(
        id=entity.id,
        placement_session_id=entity.placement_session_id,
        reading_level=entity.reading_level,
        writing_level=entity.writing_level,
        speaking_level=entity.speaking_level,
        listening_level=entity.listening_level,
        strengths_summary=entity.strengths_summary,
        weaknesses_summary=entity.weaknesses_summary,
        generated_at=entity.generated_at,
    )
