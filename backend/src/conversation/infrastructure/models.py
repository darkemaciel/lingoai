"""SQLAlchemy models for the ``conversation`` module (T044):
``ConversationSession`` / ``Message`` — the post-placement learning-loop
conversation (data-model.md). Migration:
backend/migrations/versions/0009_create_conversation_tables.py.

Like ``progression``/``gamification``/``learning_content``, no separate
framework-free domain entity — session state here is a simple two-value
enum with no transition rules complex enough to warrant a pure domain
class (unlike ``placement.PlacementSession``, whose state machine has real
invariants to enforce).
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from shared_kernel.infrastructure.db import Base


class ConversationSessionStatus(enum.StrEnum):
    ACTIVE = "active"
    ENDED = "ended"


class MessageSender(enum.StrEnum):
    STUDENT = "student"
    AGENT = "agent"


class ConversationSession(Base):
    __tablename__ = "conversation_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    status: Mapped[ConversationSessionStatus] = mapped_column(
        Enum(
            ConversationSessionStatus,
            name="conversation_session_status",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=ConversationSessionStatus.ACTIVE,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_message_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversation_sessions.id"), nullable=False, index=True
    )
    sender: Mapped[MessageSender] = mapped_column(
        Enum(
            MessageSender,
            name="message_sender",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    content_text: Mapped[str] = mapped_column(Text, nullable=False)
    audio_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
