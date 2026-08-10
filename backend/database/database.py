"""
database/database.py
--------------------
SQLAlchemy engine and session factory.

Phase 2 change:
- Now reads DATABASE_URL from the environment (via .env).
- Supports both SQLite (local dev / Streamlit fallback) and
  PostgreSQL (Supabase production).
- For PostgreSQL, removes the SQLite-only connect_args.
- For SQLite, keeps check_same_thread=False for Streamlit compatibility.

The engine is created once at module import.
All services and the FastAPI app share this same engine.
"""

import os
import sys
from pathlib import Path

# Add project root to sys.path so we can import backend.core.config
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.core.config import settings

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# ── Database URL ──────────────────────────────────────────────────────────────
# Priority:
#   1. DATABASE_URL environment variable (set in .env or deployment env)
DATABASE_URL = settings.DATABASE_URL

if not DATABASE_URL:
    raise ValueError("CRITICAL: DATABASE_URL is not set in the environment or .env file. Database connection cannot be established.")


# ── Engine configuration ──────────────────────────────────────────────────────
# SQLite needs check_same_thread=False for Streamlit's multi-thread model.
# PostgreSQL does not support this arg — it's omitted for non-SQLite.

if DATABASE_URL.startswith("sqlite"):
    raise ValueError("CRITICAL: SQLite is no longer supported. Please use a Supabase PostgreSQL connection.")

# PostgreSQL (Supabase)
# pool_pre_ping=True: test connection health before each checkout
# pool_size + max_overflow: sensible defaults for a web app
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    echo=False,
)

# ── Session factory ───────────────────────────────────────────────────────────
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# ── Declarative base ──────────────────────────────────────────────────────────
Base = declarative_base()


# ── Session dependency (used by FastAPI and services) ─────────────────────────
def get_db():
    """
    Yields a SQLAlchemy session.
    Closes the session on exit (both normal and exception paths).

    Usage as FastAPI dependency:
        db: Session = Depends(get_db)

    Usage in services:
        db = SessionLocal()
        try: ...
        finally: db.close()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()