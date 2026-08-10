"""migrations/versions/001_initial_postgres_schema.py
------------------------------------------------------
Migration: Initial PostgreSQL schema.

Creates all tables from scratch on the PostgreSQL (Supabase) database.
This migration is designed to be run ONCE on a clean PostgreSQL database.

Tables created:
  - users
  - datasets
  - audio_files           (+ audio_url column for Supabase Storage)
  - annotations
  - annotation_versions
  - review_comments
  - reviewer_approvals
  - audit_logs
  - session_tokens
  - task_locks            (Phase 7 — concurrent editing prevention)
  - super_admin_audit_logs (Phase 2 — immutable super admin audit trail)

Revision: 001
"""

from alembic import op
import sqlalchemy as sa

# Alembic metadata
revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create all tables on fresh PostgreSQL instance."""

    # ── users ─────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.String(), primary_key=True, nullable=False),
        sa.Column("username", sa.String(), unique=True, nullable=False),
        sa.Column("email", sa.String(), unique=True, nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column(
            "role",
            sa.Enum(
                "SUPER_ADMIN", "PLATFORM", "ADMIN", "ANNOTATOR", "REVIEWER",
                name="userrole"
            ),
            nullable=False,
            server_default="ANNOTATOR",
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("last_login", sa.DateTime(), nullable=True),
        sa.Column("last_seen", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_users_username", "users", ["username"])
    op.create_index("ix_users_email", "users", ["email"])

    # ── datasets ──────────────────────────────────────────────────────────────
    op.create_table(
        "datasets",
        sa.Column("id", sa.String(), primary_key=True, nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("zip_filename", sa.String(), nullable=False),
        sa.Column("language", sa.String(), nullable=False),
        sa.Column(
            "uploaded_by",
            sa.String(),
            sa.ForeignKey("users.id"),
            nullable=False
        ),
        sa.Column("total_files", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_duration", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("total_size", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("uploaded_at", sa.DateTime(), nullable=True),
    )

    # ── audio_files ───────────────────────────────────────────────────────────
    op.create_table(
        "audio_files",
        sa.Column("id", sa.String(), primary_key=True, nullable=False),
        sa.Column(
            "dataset_id",
            sa.String(),
            sa.ForeignKey("datasets.id", ondelete="CASCADE"),
            nullable=False
        ),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("original_filename", sa.String(), nullable=False),
        sa.Column("file_path", sa.String(), nullable=False),
        # Phase 3: Supabase Storage URL (NULL until storage migration runs)
        sa.Column("audio_url", sa.String(), nullable=True),
        sa.Column("language", sa.String(), nullable=False),
        sa.Column("original_transcript", sa.Text(), nullable=True),
        sa.Column("english_translation", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("duration", sa.Float(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "UNASSIGNED", "ASSIGNED", "IN_PROGRESS", "SUBMITTED", "REVIEWED",
                name="audiostatus"
            ),
            nullable=False,
            server_default="UNASSIGNED",
        ),
        sa.Column("uploaded_by", sa.String(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("assigned_to", sa.String(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_audio_files_dataset_id", "audio_files", ["dataset_id"])
    op.create_index("ix_audio_files_assigned_to", "audio_files", ["assigned_to"])
    op.create_index("ix_audio_files_status", "audio_files", ["status"])

    # ── annotations ───────────────────────────────────────────────────────────
    op.create_table(
        "annotations",
        sa.Column("id", sa.String(), primary_key=True, nullable=False),
        sa.Column(
            "audio_id",
            sa.String(),
            sa.ForeignKey("audio_files.id", ondelete="CASCADE"),
            nullable=False
        ),
        sa.Column(
            "annotator_id",
            sa.String(),
            sa.ForeignKey("users.id"),
            nullable=False
        ),
        sa.Column("transcript", sa.Text(), nullable=True),
        sa.Column("rsml_content", sa.Text(), nullable=True),
        sa.Column(
            "state",
            sa.Enum(
                "DRAFT", "SUBMITTED", "RETURNED", "APPROVED",
                name="annotationstate"
            ),
            nullable=False,
            server_default="DRAFT",
        ),
        sa.Column("submitted_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_annotations_audio_id", "annotations", ["audio_id"])
    op.create_index("ix_annotations_annotator_id", "annotations", ["annotator_id"])

    # ── annotation_versions ───────────────────────────────────────────────────
    op.create_table(
        "annotation_versions",
        sa.Column("id", sa.String(), primary_key=True, nullable=False),
        sa.Column(
            "annotation_id",
            sa.String(),
            sa.ForeignKey("annotations.id", ondelete="CASCADE"),
            nullable=False
        ),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("transcript_snapshot", sa.Text(), nullable=True),
        sa.Column("rsml_snapshot", sa.Text(), nullable=True),
        sa.Column(
            "submitted_by",
            sa.String(),
            sa.ForeignKey("users.id"),
            nullable=False
        ),
        sa.Column("submitted_at", sa.DateTime(), nullable=True),
    )

    # ── review_comments ───────────────────────────────────────────────────────
    op.create_table(
        "review_comments",
        sa.Column("id", sa.String(), primary_key=True, nullable=False),
        sa.Column(
            "annotation_id",
            sa.String(),
            sa.ForeignKey("annotations.id", ondelete="CASCADE"),
            nullable=False
        ),
        sa.Column(
            "reviewer_id",
            sa.String(),
            sa.ForeignKey("users.id"),
            nullable=False
        ),
        sa.Column("version_commented", sa.Integer(), nullable=False),
        sa.Column("span_start", sa.Integer(), nullable=True),
        sa.Column("span_end", sa.Integer(), nullable=True),
        sa.Column("comment", sa.Text(), nullable=False),
        sa.Column("is_return_reason", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )

    # ── reviewer_approvals ────────────────────────────────────────────────────
    op.create_table(
        "reviewer_approvals",
        sa.Column("id", sa.String(), primary_key=True, nullable=False),
        sa.Column(
            "annotation_id",
            sa.String(),
            sa.ForeignKey("annotations.id", ondelete="CASCADE"),
            nullable=False
        ),
        sa.Column(
            "reviewer_id",
            sa.String(),
            sa.ForeignKey("users.id"),
            nullable=False
        ),
        sa.Column("version_approved", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("PENDING", "APPROVED", "REJECTED", name="approvalstatus"),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("is_valid", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )

    # ── audit_logs ────────────────────────────────────────────────────────────
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(), primary_key=True, nullable=False),
        sa.Column(
            "user_id",
            sa.String(),
            sa.ForeignKey("users.id"),
            nullable=False
        ),
        sa.Column(
            "annotation_id",
            sa.String(),
            sa.ForeignKey("annotations.id", ondelete="SET NULL"),
            nullable=True
        ),
        sa.Column(
            "action",
            sa.Enum(
                "LOGIN", "LOGOUT", "CREATE", "UPDATE", "DELETE",
                "SUBMIT", "RETURN", "APPROVE", "REJECT",
                "IMPERSONATE", "FORCE_LOGOUT", "LOCK_USER", "UNLOCK_USER",
                "PROMOTE_USER", "DEMOTE_USER", "SYSTEM_CONFIG",
                "MAINTENANCE_MODE", "DATA_RECOVERY",
                name="auditaction"
            ),
            nullable=False,
        ),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])

    # ── session_tokens ────────────────────────────────────────────────────────
    op.create_table(
        "session_tokens",
        sa.Column("id", sa.String(), primary_key=True, nullable=False),
        sa.Column(
            "user_id",
            sa.String(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False
        ),
        sa.Column("token_hash", sa.String(), unique=True, nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_session_tokens_token_hash", "session_tokens", ["token_hash"])
    op.create_index("ix_session_tokens_user_id", "session_tokens", ["user_id"])

    # ── task_locks ────────────────────────────────────────────────────────────
    op.create_table(
        "task_locks",
        sa.Column("id", sa.String(), primary_key=True, nullable=False),
        sa.Column(
            "audio_id",
            sa.String(),
            sa.ForeignKey("audio_files.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "locked_by",
            sa.String(),
            sa.ForeignKey("users.id"),
            nullable=False
        ),
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("locked_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_task_locks_audio_id", "task_locks", ["audio_id"])
    op.create_index("ix_task_locks_expires_at", "task_locks", ["expires_at"])

    # ── super_admin_audit_logs ────────────────────────────────────────────────
    op.create_table(
        "super_admin_audit_logs",
        sa.Column("id", sa.String(), primary_key=True, nullable=False),
        sa.Column(
            "actor_id",
            sa.String(),
            sa.ForeignKey("users.id"),
            nullable=False
        ),
        sa.Column(
            "target_user_id",
            sa.String(),
            sa.ForeignKey("users.id"),
            nullable=True
        ),
        sa.Column(
            "action",
            sa.Enum(
                "LOGIN", "LOGOUT", "CREATE", "UPDATE", "DELETE",
                "SUBMIT", "RETURN", "APPROVE", "REJECT",
                "IMPERSONATE", "FORCE_LOGOUT", "LOCK_USER", "UNLOCK_USER",
                "PROMOTE_USER", "DEMOTE_USER", "SYSTEM_CONFIG",
                "MAINTENANCE_MODE", "DATA_RECOVERY",
                name="auditaction",
                # Reuse existing enum type (already created above)
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("previous_value", sa.Text(), nullable=True),
        sa.Column("new_value", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(), nullable=True),
        sa.Column("session_id", sa.String(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_super_admin_audit_logs_actor_id",
        "super_admin_audit_logs",
        ["actor_id"]
    )
    op.create_index(
        "ix_super_admin_audit_logs_created_at",
        "super_admin_audit_logs",
        ["created_at"]
    )


def downgrade() -> None:
    """Drop all tables — use with extreme caution in production."""
    op.drop_table("super_admin_audit_logs")
    op.drop_table("task_locks")
    op.drop_table("session_tokens")
    op.drop_table("audit_logs")
    op.drop_table("reviewer_approvals")
    op.drop_table("review_comments")
    op.drop_table("annotation_versions")
    op.drop_table("annotations")
    op.drop_table("audio_files")
    op.drop_table("datasets")
    op.drop_table("users")

    # Drop PostgreSQL custom enum types
    op.execute("DROP TYPE IF EXISTS userrole")
    op.execute("DROP TYPE IF EXISTS audiostatus")
    op.execute("DROP TYPE IF EXISTS annotationstate")
    op.execute("DROP TYPE IF EXISTS approvalstatus")
    op.execute("DROP TYPE IF EXISTS auditaction")
