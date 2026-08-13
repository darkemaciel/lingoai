"""Alembic migration environment.

Runs migrations with the SYNC ``psycopg`` driver
(``postgresql+psycopg://``), even though the application itself uses the
ASYNC ``asyncpg`` driver (``postgresql+asyncpg://``) via
``shared_kernel.infrastructure.db``. This is the standard Alembic pattern —
autogenerate/online mode is simplest against a plain synchronous connection
— which is why both ``asyncpg`` and ``psycopg[binary]`` are backend
dependencies by design (pyproject.toml).

DSN resolution:
- If ``ALEMBIC_DATABASE_URL`` is set, it is used as-is.
- Otherwise, it's derived from ``DATABASE_URL`` (the app's DSN) by
  normalizing the driver prefix to ``+psycopg``, regardless of what driver
  (or none) ``DATABASE_URL`` itself specifies. This normalization matters in
  practice: ``docker-compose.yml`` currently sets the backend container's
  ``DATABASE_URL`` with the ``+psycopg`` prefix (handy for this file) while
  ``shared_kernel/infrastructure/db.py`` normalizes the *same* variable to
  ``+asyncpg`` for the app engine — one env var, two consumers, each coerces
  it to the driver it actually needs.
"""

from __future__ import annotations

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# Make `src/` importable so `import shared_kernel...` / `import identity...`
# resolve, matching pyproject.toml's [tool.pytest.ini_options] pythonpath.
_SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from ai_agents.observability import agent_invocation_log  # noqa: E402,F401
from conversation.infrastructure import models as conversation_models  # noqa: E402,F401
from gamification.infrastructure import models as gamification_models  # noqa: E402,F401
from identity.infrastructure import models as identity_models  # noqa: E402,F401
from learning_content.infrastructure import models as learning_content_models  # noqa: E402,F401
from placement.infrastructure import models as placement_models  # noqa: E402,F401
from progression.infrastructure import models as progression_models  # noqa: E402,F401
from shared_kernel.infrastructure import learning_event_model  # noqa: E402,F401

# Import every module's SQLAlchemy models above so Base.metadata is fully
# populated for `alembic revision --autogenerate` in the future. The
# migrations checked into versions/ so far are hand-written (no live DB was
# available to autogenerate against), but keeping this import list current
# is what makes autogenerate usable going forward.
from shared_kernel.infrastructure.db import Base  # noqa: E402

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

DEFAULT_DATABASE_URL = "postgresql+asyncpg://lingoai:lingoai@localhost:5432/lingoai"


def _with_driver(url: str, driver: str) -> str:
    if "://" not in url:
        return url
    scheme, rest = url.split("://", 1)
    base_scheme = scheme.split("+")[0]
    return f"{base_scheme}+{driver}://{rest}"


def _sync_database_url() -> str:
    alembic_url = os.environ.get("ALEMBIC_DATABASE_URL")
    if alembic_url:
        return alembic_url
    app_url = os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)
    return _with_driver(app_url, "psycopg")


def run_migrations_offline() -> None:
    """Emit SQL to stdout without a live DB connection (`alembic upgrade --sql`)."""
    url = _sync_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live DB connection (the normal path)."""
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = _sync_database_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
