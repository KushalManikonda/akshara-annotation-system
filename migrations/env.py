"""
migrations/env.py
-----------------
Alembic environment configuration.

- Reads DATABASE_URL from environment / .env file
- Imports all SQLAlchemy models so Alembic can detect schema changes
- Supports both online (live DB) and offline (SQL script generation) modes

Phase 1: Stubs. Phase 2: Full PostgreSQL migration.
"""

import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# ── Add project paths ─────────────────────────────────────────────────────────
# We need streamlit_app/ on the path to import models
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
_STREAMLIT_APP = os.path.join(_ROOT, "streamlit_app")

for path in (_ROOT, _STREAMLIT_APP):
    if path not in sys.path:
        sys.path.insert(0, path)

# ── Load .env ─────────────────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(_ROOT, ".env"))
except ImportError:
    pass  # python-dotenv not required; rely on actual env vars

# ── Alembic config ────────────────────────────────────────────────────────────
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ── Import ALL models so Alembic can auto-detect schema ──────────────────────
# This is the canonical list of models. Update when new models are added.
from database.database import Base
from database.models import (  # noqa: F401
    User,
    Dataset,
    AudioFile,
    Annotation,
    AnnotationVersion,
    ReviewComment,
    ReviewerApproval,
    AuditLog,
    SessionToken,
)

target_metadata = Base.metadata

# ── Database URL ──────────────────────────────────────────────────────────────
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./streamlit_app/akshara.db")

# Alembic needs the URL set in the config section
config.set_main_option("sqlalchemy.url", DATABASE_URL)


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.
    Generates SQL scripts without a live DB connection.
    Useful for reviewing or auditing migrations before applying.
    """
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode with a live DB connection.
    This is the standard mode for `alembic upgrade head`.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
