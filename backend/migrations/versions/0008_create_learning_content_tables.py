"""create learning_paths, units, activities tables

Revision ID: 0008
Revises: 0007
Create Date: 2026-08-12

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# "skill" and "cefr_level" are owned by earlier migrations (0002, 0005) and
# reused here (create_type=False) — see shared_kernel/domain/enums.py.
_SKILL = postgresql.ENUM(
    "reading",
    "writing",
    "speaking",
    "listening",
    name="skill",
    create_type=False,
)
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
_ACTIVITY_TYPE = postgresql.ENUM(
    "conversation_prompt",
    "writing_exercise",
    "speaking_exercise",
    "listening_exercise",
    name="activity_type",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    _ACTIVITY_TYPE.create(bind, checkfirst=True)

    op.create_table(
        "learning_paths",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("skill", _SKILL, nullable=False),
        sa.Column("cefr_level", _CEFR_LEVEL, nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
    )

    op.create_table(
        "units",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "learning_path_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("learning_paths.id"),
            nullable=False,
        ),
        sa.Column("sequence_order", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
    )
    op.create_index("ix_units_learning_path_id", "units", ["learning_path_id"])

    op.create_table(
        "activities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "unit_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("units.id"), nullable=False
        ),
        sa.Column("type", _ACTIVITY_TYPE, nullable=False),
        sa.Column("prompt_content", postgresql.JSONB(), nullable=False),
        sa.Column("difficulty_hint", sa.Integer(), nullable=False, server_default="50"),
    )
    op.create_index("ix_activities_unit_id", "activities", ["unit_id"])


def downgrade() -> None:
    op.drop_index("ix_activities_unit_id", table_name="activities")
    op.drop_table("activities")

    op.drop_index("ix_units_learning_path_id", table_name="units")
    op.drop_table("units")

    op.drop_table("learning_paths")

    bind = op.get_bind()
    _ACTIVITY_TYPE.drop(bind, checkfirst=True)
