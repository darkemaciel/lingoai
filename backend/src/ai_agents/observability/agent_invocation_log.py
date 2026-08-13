"""``AgentInvocationLog`` SQLAlchemy model + the centralized structured-
logging wrapper that every ``AgentPort`` adapter call MUST go through
(NFR-4: "every agent call structured-logged").

Per contracts/agent-ports.md, individual adapters (``AnthropicAdapter``,
``OpenAIAdapter``, ``LocalModelAdapter``, ...) do NOT implement logging
themselves. Instead, each adapter method wraps its call in
``log_agent_invocation(...)``, which is solely responsible for writing
exactly one ``AgentInvocationLog`` row per call — whether it succeeds or
raises. This keeps observability a cross-cutting concern implemented once,
not duplicated per adapter/provider (Constitution §5, §10).

Usage inside an adapter method::

    async def assess(self, ...) -> AssessmentResult:
        async with log_agent_invocation(
            AgentName.ASSESSMENT_AGENT, self.provider, input_summary=summarize(prompt)
        ) as invocation:
            result = await self._call_llm(...)
            invocation.output_summary = summarize(result)
            return result

If the wrapped block raises, the log row is still written with
``success=False`` and a truncated ``error_message``, and the exception is
re-raised unchanged (this wrapper never swallows errors).
"""

from __future__ import annotations

import enum
import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Integer, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from shared_kernel.infrastructure.db import Base, get_session_factory

# Defensive cap on stored summaries — input/output summaries must never store
# raw PII or unbounded payloads (NFR-4: "no raw PII"). Callers are still
# responsible for redacting PII before passing a summary in; this is a
# last-resort length guard, not a redaction mechanism.
_MAX_SUMMARY_LEN = 2000


class AgentName(enum.StrEnum):
    ASSESSMENT_AGENT = "assessment_agent"
    CONVERSATION_AGENT = "conversation_agent"
    PROGRESSION_AGENT = "progression_agent"


class AgentProvider(enum.StrEnum):
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    LOCAL_MOCK = "local_mock"


class AgentInvocationLog(Base):
    """Observability only (Constitution §5, §10, NFR-4). Never read by
    domain logic — progression/gamification decisions must never depend on
    this table."""

    __tablename__ = "agent_invocation_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_name: Mapped[AgentName] = mapped_column(
        Enum(
            AgentName,
            name="agent_name",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    provider: Mapped[AgentProvider] = mapped_column(
        Enum(
            AgentProvider,
            name="agent_provider",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    input_summary: Mapped[str] = mapped_column(Text, nullable=False)
    output_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


def _truncate(text: str, max_len: int = _MAX_SUMMARY_LEN) -> str:
    return text if len(text) <= max_len else text[: max_len - 3] + "..."


class AgentInvocation:
    """Mutable handle yielded by ``log_agent_invocation``. The wrapped
    adapter call sets ``output_summary`` on it before the ``with`` block
    exits; everything else is filled in by the wrapper itself."""

    def __init__(self, agent_name: AgentName, provider: AgentProvider, input_summary: str) -> None:
        self.agent_name = agent_name
        self.provider = provider
        self.input_summary = _truncate(input_summary)
        self.output_summary: str | None = None


@asynccontextmanager
async def log_agent_invocation(
    agent_name: AgentName,
    provider: AgentProvider,
    input_summary: str,
    session: AsyncSession | None = None,
) -> AsyncIterator[AgentInvocation]:
    """Wrap a single ``AgentPort`` adapter call and write exactly one
    ``AgentInvocationLog`` row for it, success or failure.

    Args:
        agent_name: which of the three agents this call belongs to.
        provider: which concrete adapter/provider served the call.
        input_summary: a short, PII-scrubbed description of the input (the
            caller is responsible for redaction before this point).
        session: an existing ``AsyncSession`` to reuse (so the log row
            commits atomically with whatever else the caller is doing). If
            omitted, a short-lived session is opened from the shared session
            factory and committed immediately just to persist the log row.
    """
    invocation = AgentInvocation(agent_name, provider, input_summary)
    start = time.monotonic()
    success = True
    error_message: str | None = None
    try:
        yield invocation
    except Exception as exc:
        success = False
        error_message = _truncate(str(exc))
        raise
    finally:
        latency_ms = int((time.monotonic() - start) * 1000)
        log_row = AgentInvocationLog(
            agent_name=invocation.agent_name,
            provider=invocation.provider,
            input_summary=invocation.input_summary,
            output_summary=(
                _truncate(invocation.output_summary) if invocation.output_summary else None
            ),
            latency_ms=latency_ms,
            success=success,
            error_message=error_message,
        )
        await _persist(log_row, session)


async def _persist(log_row: AgentInvocationLog, session: AsyncSession | None) -> None:
    if session is not None:
        session.add(log_row)
        await session.flush()
        return
    session_factory = get_session_factory()
    async with session_factory() as owned_session:
        owned_session.add(log_row)
        await owned_session.commit()
