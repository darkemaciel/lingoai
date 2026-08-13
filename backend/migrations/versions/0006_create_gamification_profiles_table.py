"""create gamification_profiles table

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-12

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "gamification_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("xp_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("streak_current", sa.Integer(), nullable=False, server_default="0"),
        # Nullable: no activity has occurred yet when the row is first
        # bootstrapped (T029), so there is no "last activity date" until the
        # streak-update rule (T048) sets it on the first qualifying event.
        sa.Column("streak_last_activity_date", sa.Date(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("user_id", name="uq_gamification_profiles_user_id"),
    )
    op.create_index("ix_gamification_profiles_user_id", "gamification_profiles", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_gamification_profiles_user_id", table_name="gamification_profiles")
    op.drop_table("gamification_profiles")
