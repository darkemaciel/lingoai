"""create agent_invocation_logs table

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-12

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_AGENT_NAME = postgresql.ENUM(
    "assessment_agent",
    "conversation_agent",
    "progression_agent",
    name="agent_name",
    create_type=False,
)

_AGENT_PROVIDER = postgresql.ENUM(
    "anthropic",
    "openai",
    "local_mock",
    name="agent_provider",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    _AGENT_NAME.create(bind, checkfirst=True)
    _AGENT_PROVIDER.create(bind, checkfirst=True)

    op.create_table(
        "agent_invocation_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("agent_name", _AGENT_NAME, nullable=False),
        sa.Column("provider", _AGENT_PROVIDER, nullable=False),
        sa.Column("input_summary", sa.Text(), nullable=False),
        sa.Column("output_summary", sa.Text(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("agent_invocation_logs")

    bind = op.get_bind()
    _AGENT_PROVIDER.drop(bind, checkfirst=True)
    _AGENT_NAME.drop(bind, checkfirst=True)
