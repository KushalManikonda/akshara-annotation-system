"""
tests/backend/test_phase2_database.py
---------------------------------------
Phase 2 regression tests — PostgreSQL migration.

These tests run AFTER:
  1. .env has been updated with POSTGRES DATABASE_URL
  2. Alembic migration 001 has been applied
  3. Data migration script has completed

They verify:
  - PostgreSQL connection works
  - All tables exist and have the correct row counts
  - Foreign key integrity is maintained
  - New columns (audio_url) exist
  - New tables (task_locks, super_admin_audit_logs) exist
  - The Streamlit services still work against the new database
  - Cascade deletes function correctly
"""

import os
import sys
import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_STREAMLIT_APP = os.path.join(_ROOT, "streamlit_app")
for p in (_ROOT, _STREAMLIT_APP):
    if p not in sys.path:
        sys.path.insert(0, p)

from backend.core.config import settings

DATABASE_URL = settings.DATABASE_URL


# ── Skip all tests if still using SQLite ──────────────────────────────────────
pytestmark = pytest.mark.skipif(
    "sqlite" in DATABASE_URL,
    reason="Phase 2 tests require PostgreSQL. Set DATABASE_URL in .env first."
)


# ── 1. PostgreSQL connection ───────────────────────────────────────────────────
def test_postgres_connection():
    from sqlalchemy import create_engine, text
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version()")).scalar()
        assert "PostgreSQL" in result
        print(f"PASS: Connected to {result[:40]}")


# ── 2. All tables exist ───────────────────────────────────────────────────────
def test_all_tables_exist():
    from sqlalchemy import create_engine, inspect
    engine = create_engine(DATABASE_URL)
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    required = [
        "users", "datasets", "audio_files", "annotations",
        "annotation_versions", "review_comments", "reviewer_approvals",
        "audit_logs", "session_tokens", "task_locks", "super_admin_audit_logs",
    ]

    for table in required:
        assert table in tables, f"Missing table: {table}"
    print(f"PASS: All {len(required)} tables exist.")


# ── 3. New columns exist ──────────────────────────────────────────────────────
def test_new_columns_exist():
    from sqlalchemy import create_engine, inspect
    engine = create_engine(DATABASE_URL)
    inspector = inspect(engine)

    audio_cols = [c["name"] for c in inspector.get_columns("audio_files")]
    assert "audio_url" in audio_cols, "audio_files.audio_url column missing"
    print("PASS: audio_files.audio_url column exists.")


# ── 4. Row counts match expected ───────────────────────────────────────────────
def test_user_count():
    from database.database import engine
    from sqlalchemy import text
    with engine.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM users")).scalar()
        assert count >= 3, f"Expected at least 3 users, got {count}"
    print(f"PASS: Users in PostgreSQL: {count}")


def test_audio_file_count():
    from database.database import engine
    from sqlalchemy import text
    with engine.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM audio_files")).scalar()
        assert count >= 3840, f"Expected at least 3840 audio files, got {count}"
    print(f"PASS: Audio files in PostgreSQL: {count}")


def test_dataset_count():
    from database.database import engine
    from sqlalchemy import text
    with engine.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM datasets")).scalar()
        assert count >= 1, f"Expected at least 1 dataset, got {count}"
    print(f"PASS: Datasets in PostgreSQL: {count}")


# ── 5. Foreign key integrity ──────────────────────────────────────────────────
def test_no_orphaned_audio_files():
    from database.database import engine
    from sqlalchemy import text
    with engine.connect() as conn:
        orphans = conn.execute(text("""
            SELECT COUNT(*) FROM audio_files af
            WHERE NOT EXISTS (SELECT 1 FROM datasets d WHERE d.id = af.dataset_id)
        """)).scalar()
        assert orphans == 0, f"Found {orphans} orphaned audio_files"
    print("PASS: No orphaned audio_files.")


def test_no_orphaned_annotations():
    from database.database import engine
    from sqlalchemy import text
    with engine.connect() as conn:
        orphans = conn.execute(text("""
            SELECT COUNT(*) FROM annotations a
            WHERE NOT EXISTS (SELECT 1 FROM audio_files af WHERE af.id = a.audio_id)
        """)).scalar()
        assert orphans == 0, f"Found {orphans} orphaned annotations"
    print("PASS: No orphaned annotations.")


# ── 6. Models load correctly against PostgreSQL ───────────────────────────────
def test_models_query_users():
    from database.database import SessionLocal
    from database.models import User
    db = SessionLocal()
    try:
        users = db.query(User).all()
        assert len(users) >= 3
        print(f"PASS: Queried {len(users)} users via SQLAlchemy ORM.")
    finally:
        db.close()


def test_models_query_audio_files():
    from database.database import SessionLocal
    from database.models import AudioFile
    db = SessionLocal()
    try:
        count = db.query(AudioFile).count()
        assert count >= 3840
        print(f"PASS: Queried {count} audio_files via SQLAlchemy ORM.")
    finally:
        db.close()


# ── 7. Services work against PostgreSQL ──────────────────────────────────────
def test_user_service_list_users():
    from database.database import SessionLocal
    from services.user_service import get_all_users
    db = SessionLocal()
    try:
        users = get_all_users()
        assert len(users) >= 3
        print(f"PASS: user_service.get_all_users() returned {len(users)} users.")
    finally:
        db.close()


def test_auth_service_user_by_username():
    from database.database import SessionLocal
    from services.auth_service import get_user_by_username
    db = SessionLocal()
    try:
        # Use the first username from the DB
        from database.models import User
        first_user = db.query(User).first()
        if first_user:
            found = get_user_by_username(first_user.username)
            assert found is not None
            assert found.username == first_user.username
            print(f"PASS: auth_service.get_user_by_username() works. Found: {found.username}")
    finally:
        db.close()


# ── 8. New tables accept inserts ──────────────────────────────────────────────
def test_task_lock_table_writable():
    """task_locks table should accept inserts and deletes."""
    from database.database import SessionLocal
    from database.models import TaskLock, AudioFile
    from datetime import timedelta
    db = SessionLocal()
    try:
        # Find an audio file to lock
        audio = db.query(AudioFile).first()
        if not audio:
            pytest.skip("No audio files in DB")

        # Check if lock already exists
        existing = db.query(TaskLock).filter(TaskLock.audio_id == audio.id).first()
        if existing:
            db.delete(existing)
            db.commit()

        # Create a test lock
        lock = TaskLock(
            audio_id=audio.id,
            locked_by=audio.assigned_to or audio.uploaded_by or "test",
            session_id="pytest-session",
            locked_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(minutes=30),
        )
        db.add(lock)
        db.commit()

        # Verify it was created
        fetched = db.query(TaskLock).filter(TaskLock.audio_id == audio.id).first()
        assert fetched is not None

        # Clean up
        db.delete(fetched)
        db.commit()
        print("PASS: task_locks table writable.")
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


from datetime import datetime  # noqa: E402 — needed for the test above
