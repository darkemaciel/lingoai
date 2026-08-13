"""Async SQLAlchemy engine/session setup shared by every module.

- Application code uses the ASYNC engine (asyncpg driver) via
  ``get_db_session``, a FastAPI-dependency-injectable async generator.
- Alembic migrations (see ``migrations/env.py``) use a SEPARATE SYNC engine
  (psycopg driver) because Alembic's autogenerate/online-mode machinery is
  simplest against a plain synchronous connection. Both ``asyncpg`` and
  ``psycopg[binary]`` are backend dependencies by design (pyproject.toml).

Environment variables:
- ``DATABASE_URL``: the app's DSN, e.g.
  ``postgresql+asyncpg://user:pass@localhost:5432/lingoai``. The driver
  prefix is normalized to ``+asyncpg`` regardless of what is provided (see
  ``_with_driver`` below) — this matters because ``docker-compose.yml``
  currently sets ``DATABASE_URL`` with the ``+psycopg`` (sync) prefix for
  Alembic's convenience; normalizing here means the app still gets a working
  async engine either way, without requiring the two tasks to agree on one
  flavor of the same env var.
- ``ALEMBIC_DATABASE_URL`` (optional): see ``migrations/env.py`` — if unset,
  Alembic derives its sync DSN from ``DATABASE_URL`` the same way.
"""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared declarative base. Every SQLAlchemy model in the codebase
    (across all modules) MUST inherit from this so Alembic's
    ``Base.metadata`` sees every table for autogenerate support."""


DEFAULT_DATABASE_URL = "postgresql+asyncpg://lingoai:lingoai@localhost:5432/lingoai"


def _with_driver(url: str, driver: str) -> str:
    """Return ``url`` with its ``postgresql[+xxx]://`` scheme normalized to
    use ``driver`` (e.g. ``asyncpg`` or ``psycopg``), regardless of which
    driver (or none) the input URL already specifies."""
    if "://" not in url:
        return url
    scheme, rest = url.split("://", 1)
    base_scheme = scheme.split("+")[0]
    return f"{base_scheme}+{driver}://{rest}"


def _database_url() -> str:
    raw = os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)
    return _with_driver(raw, "asyncpg")


_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Lazily create (once) the process-wide async engine. Lazy so importing
    this module never requires a live DB / configured DATABASE_URL."""
    global _engine
    if _engine is None:
        _engine = create_async_engine(_database_url(), pool_pre_ping=True)
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(bind=get_engine(), expire_on_commit=False)
    return _session_factory


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: ``Depends(get_db_session)``. Yields an
    ``AsyncSession`` scoped to a single request, closed on teardown."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        yield session
