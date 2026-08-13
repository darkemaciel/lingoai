"""create placement_sessions and placement_results tables

Revision ID: 0007
Revises: 0006
Create Date: 2026-08-12

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Owned/created/dropped by this migration.
_PLACEMENT_SESSION_STATUS = postgresql.ENUM(
    "in_progress",
    "completed",
    "abandoned",
    name="placement_session_status",
    create_type=False,
)
_PLACEMENT_MODALITY = postgresql.ENUM(
    "text_only",
    "text_and_audio",
    name="placement_modality",
    create_type=False,
)

# The "cefr_level" enum type was created by 0005_create_learner_skill_profiles
# and is intentionally REUSED here (create_type=False, not created/dropped by
# this migration) so placement_results' four CEFR columns and
# learner_skill_profiles.cefr_level share one Postgres enum type — see
# shared_kernel/domain/enums.py.
_CEFR_LEVEL = postgresql.ENUM(
    "A1",
    "A2",
    "B1",
    "B2",
    "C1",
    "C2",
    name="cefr_level",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    _PLACEMENT_SESSION_STATUS.create(bind, checkfirst=True)
    _PLACEMENT_MODALITY.create(bind, checkfirst=True)

    op.create_table(
        "placement_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column("status", _PLACEMENT_SESSION_STATUS, nullable=False),
        sa.Column("modality", _PLACEMENT_MODALITY, nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_placement_sessions_user_id", "placement_sessions", ["user_id"])

    op.create_table(
        "placement_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "placement_session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("placement_sessions.id"),
            nullable=False,
        ),
        sa.Column("reading_level", _CEFR_LEVEL, nullable=False),
        sa.Column("writing_level", _CEFR_LEVEL, nullable=False),
        sa.Column("speaking_level", _CEFR_LEVEL, nullable=True),
        sa.Column("listening_level", _CEFR_LEVEL, nullable=True),
        sa.Column("strengths_summary", sa.Text(), nullable=False),
        sa.Column("weaknesses_summary", sa.Text(), nullable=False),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_unique_constraint(
        "uq_placement_results_placement_session_id",
        "placement_results",
        ["placement_session_id"],
    )


def downgrade() -> None:
    op.drop_table("placement_results")

    op.drop_index("ix_placement_sessions_user_id", table_name="placement_sessions")
    op.drop_table("placement_sessions")

    bind = op.get_bind()
    _PLACEMENT_MODALITY.drop(bind, checkfirst=True)
    _PLACEMENT_SESSION_STATUS.drop(bind, checkfirst=True)
    # _CEFR_LEVEL is NOT dropped here — it's owned by 0005, still in use by
    # learner_skill_profiles.cefr_level.
