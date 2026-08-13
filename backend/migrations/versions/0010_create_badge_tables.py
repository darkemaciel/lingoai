"""create badges, badge_awards tables

Revision ID: 0010
Revises: 0009
Create Date: 2026-08-12

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "badges",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(100), nullable=False, unique=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("criteria_description", sa.Text(), nullable=False),
    )

    op.create_table(
        "badge_awards",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column(
            "badge_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("badges.id"), nullable=False
        ),
        sa.Column(
            "awarded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_badge_awards_user_id", "badge_awards", ["user_id"])
    op.create_index("ix_badge_awards_badge_id", "badge_awards", ["badge_id"])
    op.create_unique_constraint(
        "uq_badge_awards_user_badge", "badge_awards", ["user_id", "badge_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_badge_awards_badge_id", table_name="badge_awards")
    op.drop_index("ix_badge_awards_user_id", table_name="badge_awards")
    op.drop_table("badge_awards")
    op.drop_table("badges")
