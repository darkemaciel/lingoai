"""SQLAlchemy models for the ``identity`` module.

``User`` fields/constraints per specs/001-placement-learning-loop/data-model.md
("User" table). Migration: backend/migrations/versions/0001_create_users_table.py.

``RefreshToken`` is not one of data-model.md's Key Entities — it is an
identity-module infrastructure detail needed to satisfy research.md §10's
"refresh token ... stored server-side in PostgreSQL (hashed, revocable)".
Only the SHA-256 hash of the opaque refresh token is stored, never the raw
token (mirrors ``password_hash`` — never store a secret we can avoid
storing in recoverable form). Migration:
backend/migrations/versions/0004_create_refresh_tokens_table.py.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from shared_kernel.infrastructure.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    native_language: Mapped[str | None] = mapped_column(String(2), nullable=True)  # ISO 639-1
    timezone: Mapped[str] = mapped_column(String(64), nullable=False)  # IANA tz name
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
