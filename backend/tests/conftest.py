"""Shared pytest fixtures.

- ``db_session``: an ``AsyncSession`` scoped to a single test, wrapped in a
  transaction that's rolled back at teardown (test isolation without
  recreating the schema every test). Requires a reachable Postgres — see
  ``docker-compose.yml``'s ``postgres`` service, or set ``TEST_DATABASE_URL``.
  Per quickstart.md Scenario 8, the full suite is expected to run via
  ``docker compose exec backend pytest``, where Postgres is always up; if no
  DB is reachable (e.g. running `pytest` directly without
  `docker compose up -d postgres`), any test that requests ``db_session``
  is SKIPPED rather than erroring, so pure unit-level tests (no DB) still
  run standalone.
- ``client``: an ``httpx.AsyncClient`` (ASGI-transport, no real socket)
  wired to reuse ``db_session`` via a dependency override, so requests made
  through it see the same transaction (and therefore the same
  rollback-based isolation). Deliberately *not* ``fastapi.testclient
  .TestClient``: that class drives the ASGI app from a background thread
  with its own event loop, so any asyncpg connection opened by
  ``db_session`` (bound to the outer pytest-asyncio loop) would be used
  from a different loop mid-request and raise "Future attached to a
  different loop". Running the client in-loop via ``ASGITransport``
  sidesteps that entirely.
- ``local_model_adapter`` / ``null_audio_adapter``: ready-to-use
  deterministic agent-port adapters (NFR-7 — no live LLM/network calls in
  tests).
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from dataclasses import dataclass

import pytest
import pytest_asyncio
import sqlalchemy as sa
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from ai_agents.adapters.local_model_adapter import (
    ASSESSMENT_TURNS_BEFORE_COMPLETE,
    LocalModelAdapter,
)
from ai_agents.adapters.null_audio_adapter import NullAudioAdapter

# Import every module's SQLAlchemy models so Base.metadata is fully
# populated before `create_all` runs below — mirrors migrations/env.py's
# import list (see that file's comment for why this must stay current).
from ai_agents.observability import agent_invocation_log  # noqa: F401
from app import app
from conversation.infrastructure import models as conversation_models  # noqa: F401
from identity.infrastructure import models as identity_models  # noqa: F401
from identity.infrastructure.security import create_access_token
from learning_content.infrastructure import models as learning_content_models  # noqa: F401
from shared_kernel.infrastructure import learning_event_model  # noqa: F401
from shared_kernel.infrastructure.db import Base, get_db_session
from shared_kernel.infrastructure.rate_limiter import reset_rate_limiter


def _test_database_url() -> str:
    import os

    raw = os.environ.get(
        "TEST_DATABASE_URL",
        os.environ.get(
            "DATABASE_URL", "postgresql+asyncpg://lingoai:lingoai@localhost:5432/lingoai"
        ),
    )
    if "://" not in raw:
        return raw
    scheme, rest = raw.split("://", 1)
    return f"{scheme.split('+')[0]}+asyncpg://{rest}"


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(_test_database_url())
    try:
        async with engine.connect() as probe:
            await probe.execute(sa.text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 - any connectivity failure means "skip"
        await engine.dispose()
        pytest.skip(f"no reachable test database ({_test_database_url()}): {exc}")

    async with engine.begin() as setup_conn:
        await setup_conn.run_sync(Base.metadata.create_all)

    connection = await engine.connect()
    transaction = await connection.begin()
    session_factory = async_sessionmaker(
        bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint"
    )
    session = session_factory()
    try:
        yield session
    finally:
        await session.close()
        await transaction.rollback()
        await connection.close()
        await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def _override_get_db_session() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db_session] = _override_get_db_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as test_client:
        yield test_client
    app.dependency_overrides.pop(get_db_session, None)


@pytest.fixture(autouse=True)
def _reset_rate_limiter() -> None:
    """Each test starts with a clean rate-limit window — otherwise the
    in-memory limiter's process-global state (shared_kernel/infrastructure/
    rate_limiter.py, T071) would accumulate hits across the whole test
    session and eventually 429 unrelated tests that legitimately call
    `/auth/*` more than a handful of times (e.g. every `placed_student`
    fixture use)."""
    reset_rate_limiter()


@pytest.fixture
def local_model_adapter() -> LocalModelAdapter:
    return LocalModelAdapter()


@pytest.fixture
def null_audio_adapter() -> NullAudioAdapter:
    return NullAudioAdapter()


@dataclass(frozen=True)
class PlacedStudent:
    """A fresh, fully-placed student — the functional precondition US2's
    Independent Test requires (spec.md: "With a pre-existing placed
    student..."). `user_id`/`token` let a test hit any protected route
    directly without re-running the placement flow itself."""

    user_id: str
    token: str


@pytest_asyncio.fixture
async def placed_student(client: AsyncClient) -> PlacedStudent:
    """Registers a fresh user and drives their placement session to
    completion through the real API (bootstrapping `LearnerSkillProfile`/
    `GamificationProfile` rows per T029), returning credentials for the
    resulting placed student."""
    email = f"student-{uuid.uuid4()}@example.com"
    register_response = await client.post(
        "/api/v1/auth/register", json={"email": email, "password": "s3cret!!!"}
    )
    user_id = register_response.json()["user_id"]
    access_token, _ = create_access_token(uuid.UUID(user_id))
    headers = {"Authorization": f"Bearer {access_token}"}

    start_response = await client.post("/api/v1/placement/sessions", headers=headers)
    session_id = start_response.json()["placement_session_id"]
    for turn in range(ASSESSMENT_TURNS_BEFORE_COMPLETE):
        await client.post(
            f"/api/v1/placement/sessions/{session_id}/answers",
            headers=headers,
            json={
                "client_submission_id": str(uuid.uuid4()),
                "content_text": f"placement answer {turn}",
            },
        )

    return PlacedStudent(user_id=user_id, token=access_token)
