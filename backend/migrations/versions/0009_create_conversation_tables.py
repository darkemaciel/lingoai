"""create conversation_sessions, messages tables

Revision ID: 0009
Revises: 0008
Create Date: 2026-08-12

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CONVERSATION_SESSION_STATUS = postgresql.ENUM(
    "active",
    "ended",
    name="conversation_session_status",
    create_type=False,
)
_MESSAGE_SENDER = postgresql.ENUM(
    "student",
    "agent",
    name="message_sender",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    _CONVERSATION_SESSION_STATUS.create(bind, checkfirst=True)
    _MESSAGE_SENDER.create(bind, checkfirst=True)

    op.create_table(
        "conversation_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column("status", _CONVERSATION_SESSION_STATUS, nullable=False),
        sa.Column(
            "started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "last_message_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_conversation_sessions_user_id", "conversation_sessions", ["user_id"]
    )

    op.create_table(
        "messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "conversation_session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("conversation_sessions.id"),
            nullable=False,
        ),
        sa.Column("sender", _MESSAGE_SENDER, nullable=False),
        sa.Column("content_text", sa.Text(), nullable=False),
        sa.Column("audio_ref", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_messages_conversation_session_id", "messages", ["conversation_session_id"])


def downgrade() -> None:
    op.drop_index("ix_messages_conversation_session_id", table_name="messages")
    op.drop_table("messages")

    op.drop_index("ix_conversation_sessions_user_id", table_name="conversation_sessions")
    op.drop_table("conversation_sessions")

    bind = op.get_bind()
    _MESSAGE_SENDER.drop(bind, checkfirst=True)
    _CONVERSATION_SESSION_STATUS.drop(bind, checkfirst=True)
