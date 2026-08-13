"""create learning_events table

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-12

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# create_type=False: the ENUM types are created/dropped explicitly below so
# op.create_table() doesn't also try to emit CREATE TYPE (which would either
# double-create or race depending on SQLAlchemy version). The "skill" enum
# type in particular is intentionally reused (not recreated) by a later
# migration that adds LearnerSkillProfile.skill (T025) — see
# shared_kernel/domain/enums.py.
_LEARNING_EVENT_TYPE = postgresql.ENUM(
    "placement_answer_submitted",
    "exercise_answer_submitted",
    "conversation_turn_completed",
    "level_advanced",
    "badge_awarded",
    name="learning_event_type",
    create_type=False,
)

_SKILL = postgresql.ENUM(
    "reading",
    "writing",
    "speaking",
    "listening",
    name="skill",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    _LEARNING_EVENT_TYPE.create(bind, checkfirst=True)
    _SKILL.create(bind, checkfirst=True)

    op.create_table(
        "learning_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("event_type", _LEARNING_EVENT_TYPE, nullable=False),
        sa.Column("skill", _SKILL, nullable=True),
        # Nullable, no FK yet — the owning tables (activities, placement
        # sessions, conversation sessions) don't exist until later tasks
        # (T027, T043, T044). See shared_kernel/infrastructure/learning_event_model.py.
        sa.Column("activity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("placement_session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("conversation_session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("client_submission_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("payload", postgresql.JSONB, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "user_id",
            "client_submission_id",
            name="uq_learning_events_user_client_submission",
        ),
    )
    op.create_index("ix_learning_events_user_id", "learning_events", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_learning_events_user_id", table_name="learning_events")
    op.drop_table("learning_events")

    bind = op.get_bind()
    _SKILL.drop(bind, checkfirst=True)
    _LEARNING_EVENT_TYPE.drop(bind, checkfirst=True)
