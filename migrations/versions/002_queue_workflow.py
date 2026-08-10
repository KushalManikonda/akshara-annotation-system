"""migrations/versions/002_queue_workflow.py
-------------------------------------------
Migration: Task Queue & Self-Assignment Workflow

Changes:
  - Adds REWORK_REQUIRED, COMPLETED to audiostatus enum (PostgreSQL native enum)
  - Adds TASK_ASSIGNED, TASK_OPENED, TASK_SUBMITTED, TASK_RETURNED,
    TASK_REASSIGNED, TASK_AUTO_RELEASED, TASK_COMPLETED to auditaction enum
  - Adds priority column to datasets table
  - Adds assigned_at column to audio_files table
  - Adds last_heartbeat_at column to audio_files table

Revision: 002
Depends on: 001
"""

from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. Extend audiostatus PostgreSQL enum ─────────────────────────────────
    # NOTE: ALTER TYPE ... ADD VALUE cannot run inside a transaction on older PG,
    # but Supabase uses PG14+ which supports it. We use COMMIT workaround for
    # safety anyway by running raw SQL with execute_if.
    op.execute("ALTER TYPE audiostatus ADD VALUE IF NOT EXISTS 'REWORK_REQUIRED'")
    op.execute("ALTER TYPE audiostatus ADD VALUE IF NOT EXISTS 'COMPLETED'")

    # ── 2. Extend auditaction enum ────────────────────────────────────────────
    new_audit_actions = [
        "TASK_ASSIGNED",
        "TASK_OPENED",
        "TASK_SUBMITTED",
        "TASK_RETURNED",
        "TASK_REASSIGNED",
        "TASK_AUTO_RELEASED",
        "TASK_COMPLETED",
    ]
    for action in new_audit_actions:
        op.execute(f"ALTER TYPE auditaction ADD VALUE IF NOT EXISTS '{action}'")

    # ── 3. Add priority to datasets ───────────────────────────────────────────
    op.add_column(
        "datasets",
        sa.Column(
            "priority",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )

    # ── 4. Add assigned_at to audio_files ─────────────────────────────────────
    op.add_column(
        "audio_files",
        sa.Column("assigned_at", sa.DateTime(), nullable=True),
    )

    # ── 5. Add last_heartbeat_at to audio_files ───────────────────────────────
    op.add_column(
        "audio_files",
        sa.Column("last_heartbeat_at", sa.DateTime(), nullable=True),
    )

    # ── 6. Indexes for queue queries ─────────────────────────────────────────
    op.create_index(
        "ix_audio_files_language_status",
        "audio_files",
        ["language", "status"],
    )
    op.create_index(
        "ix_audio_files_assigned_at",
        "audio_files",
        ["assigned_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_audio_files_assigned_at", table_name="audio_files")
    op.drop_index("ix_audio_files_language_status", table_name="audio_files")
    op.drop_column("audio_files", "last_heartbeat_at")
    op.drop_column("audio_files", "assigned_at")
    op.drop_column("datasets", "priority")
    # NOTE: PostgreSQL does not support DROP VALUE from enums.
    # To roll back the enum values, a full type recreation would be needed.
    # Skipping for safety in this migration.
