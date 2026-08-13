"""SQLAlchemy model for ``GamificationProfile`` — one row per user (1:1),
per data-model.md "GamificationProfile". Migration:
backend/migrations/versions/0006_create_gamification_profiles_table.py.

Model/table only (T026). The XP formula (research.md §7) and the
timezone-aware, no-tolerance streak update rule are implemented later by
T047 (``gamification/domain/xp_rule.py``) and T048
(``gamification/domain/streak_rule.py``). Nothing here enforces those
rules; this module just stores the columns.

The bootstrap side effect described in data-model.md ("PlacementResult
creation creates one GamificationProfile row if the user doesn't have one
yet") is implemented by T029 in the ``placement`` module's application
service, not here.

Also holds ``Badge``/``BadgeAward`` (T045) — the badge catalog and awards
table. Migration: backend/migrations/versions/0010_create_badge_tables.py.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from shared_kernel.infrastructure.db import Base


class GamificationProfile(Base):
    __tablename__ = "gamification_profiles"
    __table_args__ = (UniqueConstraint("user_id", name="uq_gamification_profiles_user_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    # Sum of all xp_awarded (research.md §7). Formula applied by T047, not here.
    xp_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Consecutive days with >= 1 completed activity. Update rule applied by
    # T048, not here.
    streak_current: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # In the user's `timezone` (User.timezone) — used to detect a missed day.
    streak_last_activity_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Badge(Base):
    """Catalog (T045) — seed data, not user-generated. See
    ``gamification/infrastructure/seed.py`` and
    ``gamification/domain/badge_rule.py`` for the fixed set of codes this
    iteration awards (`first_conversation_completed`, `streak_7_days`,
    `first_level_advanced`)."""

    __tablename__ = "badges"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    criteria_description: Mapped[str] = mapped_column(Text, nullable=False)


class BadgeAward(Base):
    __tablename__ = "badge_awards"
    __table_args__ = (UniqueConstraint("user_id", "badge_id", name="uq_badge_awards_user_badge"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    badge_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("badges.id"), nullable=False, index=True
    )
    awarded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
