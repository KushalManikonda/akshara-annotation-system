#!/usr/bin/env python3
"""
scripts/migrate_sqlite_to_postgres.py
---------------------------------------
Data migration: SQLite → Supabase PostgreSQL

This script:
1. Reads ALL rows from the local akshara.db (SQLite)
2. Writes them to the Supabase PostgreSQL database
3. Verifies row counts match after migration
4. Reports any discrepancies

Usage:
    python scripts/migrate_sqlite_to_postgres.py

Requirements:
    - .env file with DATABASE_URL set to the PostgreSQL connection string
    - The Alembic migration (001_initial_postgres_schema.py) must already
      have been applied: `alembic -c migrations/alembic.ini upgrade head`
    - pip install psycopg2-binary python-dotenv

Run from the project root (Akshara-Annotation-Platform-main/).
"""

import os
import sys
import json
from datetime import datetime

# ── Path setup ────────────────────────────────────────────────────────────────
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_STREAMLIT_APP = os.path.join(_ROOT, "streamlit_app")
sys.path.insert(0, _ROOT)
sys.path.insert(0, _STREAMLIT_APP)

# ── Load .env ─────────────────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(_ROOT, ".env"))
    print("[INFO] Loaded .env")
except ImportError:
    print("[WARN] python-dotenv not installed — relying on shell environment variables")

# ── Verify PostgreSQL URL is set ──────────────────────────────────────────────
POSTGRES_URL = os.environ.get("DATABASE_URL", "")
if not POSTGRES_URL or "sqlite" in POSTGRES_URL:
    print("[ERROR] DATABASE_URL must be set to a PostgreSQL connection string.")
    print("        Current value:", POSTGRES_URL or "(empty)")
    print("        Set it in your .env file and re-run.")
    sys.exit(1)

print(f"[INFO] Target PostgreSQL: {POSTGRES_URL[:60]}...")

SQLITE_URL = "sqlite:///" + os.path.join(_ROOT, "akshara.db")
print(f"[INFO] Source SQLite: {SQLITE_URL}")

# ── Create engines ────────────────────────────────────────────────────────────
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

sqlite_engine = create_engine(
    SQLITE_URL,
    connect_args={"check_same_thread": False}
)

pg_engine = create_engine(
    POSTGRES_URL,
    pool_pre_ping=True,
)

SqliteSession = sessionmaker(bind=sqlite_engine)
PgSession = sessionmaker(bind=pg_engine)


# ── Helper: safe row count comparison ─────────────────────────────────────────
def count(engine, table_name: str) -> int:
    with engine.connect() as conn:
        result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
        return result.scalar()


# ── Migration: table by table ─────────────────────────────────────────────────
# Order matters — parent tables first (FK constraints)
TABLE_ORDER = [
    "users",
    "datasets",
    "audio_files",
    "annotations",
    "annotation_versions",
    "review_comments",
    "reviewer_approvals",
    "audit_logs",
    "session_tokens",
    # task_locks and super_admin_audit_logs start empty (new tables)
]

results = {}

print("\n" + "="*60)
print("STARTING DATA MIGRATION: SQLite --> PostgreSQL")
print("="*60 + "\n")


def migrate_table(table_name: str):
    """Read all rows from SQLite table, write to PostgreSQL."""

    with sqlite_engine.connect() as src_conn:
        rows = src_conn.execute(text(f"SELECT * FROM {table_name}")).mappings().all()

    if not rows:
        print(f"  [SKIP] {table_name}: 0 rows -- nothing to migrate")
        results[table_name] = {"sqlite": 0, "postgres": 0, "ok": True}
        return

    # Convert rows to plain dicts and fix booleans
    bool_columns = {'is_active', 'is_return_reason', 'is_valid'}
    row_dicts = []
    for r in rows:
        d = dict(r)
        for k in bool_columns:
            if k in d and d[k] is not None:
                d[k] = bool(d[k])
        row_dicts.append(d)

    # Write to PostgreSQL in batches of 500
    BATCH_SIZE = 500
    pg_session = PgSession()

    try:
        for i in range(0, len(row_dicts), BATCH_SIZE):
            batch = row_dicts[i:i + BATCH_SIZE]
            try:
                pg_session.execute(
                    text(f"INSERT INTO {table_name} ({', '.join(batch[0].keys())}) "
                         f"VALUES ({', '.join(':' + k for k in batch[0].keys())}) "
                         f"ON CONFLICT (id) DO NOTHING"),
                    batch,
                )
                pg_session.commit()
                print(f"  [BATCH] {table_name}: inserted rows {i+1}-{min(i+BATCH_SIZE, len(row_dicts))}")
            except Exception as batch_e:
                pg_session.rollback()
                print(f"  [WARN] Batch insert failed for {table_name}, falling back to row-by-row...")
                for row in batch:
                    try:
                        pg_session.execute(
                            text(f"INSERT INTO {table_name} ({', '.join(row.keys())}) "
                                 f"VALUES ({', '.join(':' + k for k in row.keys())}) "
                                 f"ON CONFLICT (id) DO NOTHING"),
                            [row],
                        )
                        pg_session.commit()
                    except Exception as row_e:
                        pg_session.rollback()
                        print(f"  [SKIP] {table_name} id={row.get('id')}: {row_e}".split('\n')[0])

        # Verify count
        src_count = len(row_dicts)
        dst_count = count(pg_engine, table_name)

        ok = src_count == dst_count
        results[table_name] = {
            "sqlite": src_count,
            "postgres": dst_count,
            "ok": ok,
        }

        status = "OK" if ok else "MISMATCH"
        print(f"  [{status}] {table_name}: SQLite={src_count}, Postgres={dst_count}")

    except Exception as e:
        pg_session.rollback()
        print(f"  [ERROR] {table_name}: {e}")
        results[table_name] = {"sqlite": len(row_dicts), "postgres": 0, "ok": False, "error": str(e)}
    finally:
        pg_session.close()


# Run migration for each table
for table in TABLE_ORDER:
    print(f"\nMigrating: {table}")
    migrate_table(table)


# -- Summary -------------------------------------------------------------------
print("\n" + "="*60)
print("MIGRATION SUMMARY")
print("="*60)
print(f"{'Table':<30} {'SQLite':>8} {'Postgres':>10} {'Status':>8}")
print("-"*60)

all_ok = True
for table, r in results.items():
    status = "OK" if r["ok"] else "FAIL"
    if not r["ok"]:
        all_ok = False
    print(f"{table:<30} {r['sqlite']:>8} {r['postgres']:>10} {status:>8}")

print("="*60)

if all_ok:
    print("\n[SUCCESS] All tables migrated successfully.")
    print("          You can now update DATABASE_URL in .env to PostgreSQL.")
    print("          The Streamlit app will reconnect automatically on next start.")
else:
    print("\n[FAILURE] Some tables did not migrate cleanly.")
    print("          Review errors above and re-run for failed tables.")
    sys.exit(1)


# -- Foreign key integrity check -----------------------------------------------
print("\n" + "="*60)
print("FOREIGN KEY INTEGRITY CHECK")
print("="*60)

FK_CHECKS = [
    ("audio_files", "dataset_id", "datasets", "id"),
    ("annotations", "audio_id", "audio_files", "id"),
    ("annotations", "annotator_id", "users", "id"),
    ("annotation_versions", "annotation_id", "annotations", "id"),
    ("review_comments", "annotation_id", "annotations", "id"),
    ("reviewer_approvals", "annotation_id", "annotations", "id"),
    ("audit_logs", "user_id", "users", "id"),
    ("session_tokens", "user_id", "users", "id"),
]

with pg_engine.connect() as conn:
    for child_table, child_col, parent_table, parent_col in FK_CHECKS:
        orphan_count = conn.execute(text(f"""
            SELECT COUNT(*) FROM {child_table} c
            WHERE c.{child_col} IS NOT NULL
              AND NOT EXISTS (
                SELECT 1 FROM {parent_table} p WHERE p.{parent_col} = c.{child_col}
              )
        """)).scalar()

        status = "OK" if orphan_count == 0 else f"ORPHANS: {orphan_count}"
        print(f"  {child_table}.{child_col} -- {parent_table}.{parent_col}: {status}")

print("[DONE] Migration complete.")
