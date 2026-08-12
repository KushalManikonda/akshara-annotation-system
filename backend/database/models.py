"""
database/models.py
------------------
SQLAlchemy ORM models for the Akshara Annotation Platform.

Phase 2 changes (non-breaking additions only):
- Added cascade="all, delete-orphan" on all parent→child relationships
  so deleting a Dataset deletes all child rows atomically.
- Added TaskLock model for concurrent editing prevention (Phase 7).
- Added SuperAdminAuditLog model for immutable audit trail (Phase 2).
- audio_url column added to AudioFile for Supabase Storage URLs (Phase 3).
- audio_relative_path: portable relative path e.g. 'Telugu/telugu1.wav' (Phase 4).
- audio_storage_type: 'local' | 'supabase' — NULL treated as 'supabase' for backward compat (Phase 4).

All existing model fields, table names, and relationships are preserved.
"""

from uuid import uuid4
from datetime import datetime
from backend.database.database import Base
from sqlalchemy.orm import relationship

from sqlalchemy import (
    Column,
    String,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Text,
    Integer,
    Boolean,
    UniqueConstraint,
)

from backend.database.enums import (
    UserRole,
    AudioStatus,
    AnnotationState,
    ApprovalStatus,
    AuditAction,
)


# ──────────────────────────────────────────────────────────────────────────────
# User
# ──────────────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(
        String,
        primary_key=True,
        default=lambda: str(uuid4())
    )

    username = Column(
        String,
        unique=True,
        nullable=False
    )

    email = Column(
        String,
        unique=True,
        nullable=False
    )

    password_hash = Column(
        String,
        nullable=False
    )

    role = Column(
        Enum(UserRole),
        nullable=False,
        default=UserRole.ANNOTATOR
    )

    is_active = Column(
        Boolean,
        default=True
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    last_login = Column(
        DateTime,
        nullable=True
    )

    last_seen = Column(
        DateTime,
        nullable=True
    )


# ──────────────────────────────────────────────────────────────────────────────
# Dataset
# ──────────────────────────────────────────────────────────────────────────────

class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(
        String,
        primary_key=True,
        default=lambda: str(uuid4())
    )

    name = Column(
        String,
        nullable=False
    )

    zip_filename = Column(
        String,
        nullable=False
    )

    language = Column(
        String,
        nullable=False
    )

    uploaded_by = Column(
        String,
        ForeignKey("users.id"),
        nullable=False
    )

    total_files = Column(
        Integer,
        default=0,
        nullable=False
    )

    total_duration = Column(
        Float,
        default=0.0,
        nullable=False
    )

    uploaded_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    # Higher priority = assigned first in the queue (default 0)
    priority = Column(
        Integer,
        nullable=False,
        default=0
    )

    uploader = relationship("User")

    total_size = Column(
        Float,
        default=0.0,
        nullable=False
    )

    # CASCADE: deleting a Dataset deletes all its AudioFiles (and their children)
    audio_files = relationship(
        "AudioFile",
        back_populates="dataset",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


# ──────────────────────────────────────────────────────────────────────────────
# AudioFile
# ──────────────────────────────────────────────────────────────────────────────

class AudioFile(Base):
    __tablename__ = "audio_files"

    id = Column(
        String,
        primary_key=True,
        default=lambda: str(uuid4())
    )

    dataset_id = Column(
        String,
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False
    )

    dataset = relationship(
        "Dataset",
        back_populates="audio_files",
    )

    filename = Column(
        String,
        nullable=False
    )

    original_filename = Column(
        String,
        nullable=False
    )

    # Phase 1–2: local file path. Phase 3+: Supabase Storage key (use audio_url)
    file_path = Column(
        String,
        nullable=False
    )

    # Phase 3+: Supabase Storage signed/public URL.
    # NULL during Phase 1–2; populated after storage migration.
    audio_url = Column(
        String,
        nullable=True
    )

    # Phase 4+: Portable relative audio path stored in DB (no machine-specific prefix).
    # Example: 'Telugu/telugu1.wav'
    # Resolved at runtime as: AUDIO_ROOT_DIR + '/' + audio_relative_path
    # NULL for old records that pre-date this column.
    audio_relative_path = Column(
        String,
        nullable=True
    )

    # Phase 4+: 'local' (WAV stored outside Supabase, user picks locally in browser)
    # or 'supabase' (WAV uploaded to Supabase Storage).
    # NULL for old records — treated as 'supabase' by the application for backward compat.
    audio_storage_type = Column(
        String,
        nullable=True
    )

    language = Column(
        String,
        nullable=False
    )

    original_transcript = Column(
        Text,
        nullable=True
    )

    english_translation = Column(
        Text,
        nullable=True
    )

    metadata_json = Column(
        Text,
        nullable=True
    )

    duration = Column(
        Float,
        nullable=True,
        default=0.0
    )

    status = Column(
        Enum(AudioStatus),
        nullable=False,
        default=AudioStatus.UNASSIGNED
    )

    uploaded_by = Column(
        String,
        ForeignKey("users.id"),
        nullable=True
    )

    assigned_to = Column(
        String,
        ForeignKey("users.id"),
        nullable=True
    )

    uploaded_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    # Set when task is assigned via queue — used for abandoned-task timeout
    assigned_at = Column(
        DateTime,
        nullable=True
    )

    # Updated by heartbeat from annotator workspace — used for in-progress timeout
    last_heartbeat_at = Column(
        DateTime,
        nullable=True
    )

    uploader = relationship(
        "User",
        foreign_keys=[uploaded_by]
    )

    assignee = relationship(
        "User",
        foreign_keys=[assigned_to]
    )

    # CASCADE: deleting an AudioFile deletes all its Annotations
    annotations = relationship(
        "Annotation",
        back_populates="audio",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    # CASCADE: deleting an AudioFile releases its TaskLock
    task_lock = relationship(
        "TaskLock",
        back_populates="audio",
        cascade="all, delete-orphan",
        uselist=False,
        passive_deletes=True,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Annotation
# ──────────────────────────────────────────────────────────────────────────────

class Annotation(Base):
    __tablename__ = "annotations"

    id = Column(
        String,
        primary_key=True,
        default=lambda: str(uuid4())
    )

    audio_id = Column(
        String,
        ForeignKey("audio_files.id", ondelete="CASCADE"),
        nullable=False
    )

    annotator_id = Column(
        String,
        ForeignKey("users.id"),
        nullable=False
    )

    transcript = Column(
        Text,
        nullable=True
    )

    rsml_content = Column(
        Text,
        nullable=True
    )

    state = Column(
        Enum(AnnotationState),
        default=AnnotationState.DRAFT,
        nullable=False
    )

    submitted_at = Column(
        DateTime,
        nullable=True
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    audio = relationship(
        "AudioFile",
        back_populates="annotations",
    )

    annotator = relationship(
        "User",
        foreign_keys=[annotator_id]
    )

    # CASCADE: deleting Annotation deletes all its versions, comments, approvals
    versions = relationship(
        "AnnotationVersion",
        back_populates="annotation",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    comments = relationship(
        "ReviewComment",
        back_populates="annotation",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    approvals = relationship(
        "ReviewerApproval",
        back_populates="annotation",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    audit_logs = relationship(
        "AuditLog",
        back_populates="annotation",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


# ──────────────────────────────────────────────────────────────────────────────
# AnnotationVersion
# ──────────────────────────────────────────────────────────────────────────────

class AnnotationVersion(Base):
    __tablename__ = "annotation_versions"

    id = Column(
        String,
        primary_key=True,
        default=lambda: str(uuid4())
    )

    annotation_id = Column(
        String,
        ForeignKey("annotations.id", ondelete="CASCADE"),
        nullable=False
    )

    version_number = Column(
        Integer,
        nullable=False
    )

    transcript_snapshot = Column(
        Text,
        nullable=True
    )

    rsml_snapshot = Column(
        Text,
        nullable=True
    )

    submitted_by = Column(
        String,
        ForeignKey("users.id"),
        nullable=False
    )

    submitted_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    annotation = relationship(
        "Annotation",
        back_populates="versions",
    )

    submitter = relationship("User")


# ──────────────────────────────────────────────────────────────────────────────
# ReviewComment
# ──────────────────────────────────────────────────────────────────────────────

class ReviewComment(Base):
    __tablename__ = "review_comments"

    id = Column(
        String,
        primary_key=True,
        default=lambda: str(uuid4())
    )

    annotation_id = Column(
        String,
        ForeignKey("annotations.id", ondelete="CASCADE"),
        nullable=False
    )

    reviewer_id = Column(
        String,
        ForeignKey("users.id"),
        nullable=False
    )

    version_commented = Column(
        Integer,
        nullable=False
    )

    span_start = Column(
        Integer,
        nullable=True
    )

    span_end = Column(
        Integer,
        nullable=True
    )

    comment = Column(
        Text,
        nullable=False
    )

    is_return_reason = Column(
        Boolean,
        default=False
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    annotation = relationship(
        "Annotation",
        back_populates="comments",
    )

    reviewer = relationship("User")


# ──────────────────────────────────────────────────────────────────────────────
# ReviewerApproval
# ──────────────────────────────────────────────────────────────────────────────

class ReviewerApproval(Base):
    __tablename__ = "reviewer_approvals"

    id = Column(
        String,
        primary_key=True,
        default=lambda: str(uuid4())
    )

    annotation_id = Column(
        String,
        ForeignKey("annotations.id", ondelete="CASCADE"),
        nullable=False
    )

    reviewer_id = Column(
        String,
        ForeignKey("users.id"),
        nullable=False
    )

    version_approved = Column(
        Integer,
        nullable=False
    )

    status = Column(
        Enum(ApprovalStatus),
        default=ApprovalStatus.PENDING,
        nullable=False
    )

    is_valid = Column(
        Boolean,
        default=True
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    annotation = relationship(
        "Annotation",
        back_populates="approvals",
    )

    reviewer = relationship("User")


# ──────────────────────────────────────────────────────────────────────────────
# AuditLog
# ──────────────────────────────────────────────────────────────────────────────

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(
        String,
        primary_key=True,
        default=lambda: str(uuid4())
    )

    user_id = Column(
        String,
        ForeignKey("users.id"),
        nullable=False
    )

    annotation_id = Column(
        String,
        ForeignKey("annotations.id", ondelete="SET NULL"),
        nullable=True
    )

    action = Column(
        Enum(AuditAction),
        nullable=False
    )

    details = Column(
        Text,
        nullable=True
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    user = relationship("User")

    annotation = relationship(
        "Annotation",
        back_populates="audit_logs",
    )


# ──────────────────────────────────────────────────────────────────────────────
# SessionToken (persists login across browser refreshes — Streamlit sessions)
# ──────────────────────────────────────────────────────────────────────────────

class SessionToken(Base):
    __tablename__ = "session_tokens"

    id = Column(
        String,
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    user_id = Column(
        String,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Store only the hash — never the raw token
    token_hash = Column(
        String,
        unique=True,
        nullable=False,
        index=True,
    )

    expires_at = Column(
        DateTime,
        nullable=False,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
    )

    user = relationship("User")


# ──────────────────────────────────────────────────────────────────────────────
# TaskLock  (Phase 7 — prevents concurrent editing of the same task)
# ──────────────────────────────────────────────────────────────────────────────

class TaskLock(Base):
    """
    Server-side lock on an audio task.

    When an annotator opens a task workspace, a lock is created.
    The workspace sends a heartbeat every 60s to extend expires_at.
    If the heartbeat stops (tab closed, network lost), the lock
    auto-expires after TASK_LOCK_TIMEOUT_MINUTES (default 30 min).

    Only the lock holder or an admin can release a lock early.
    """
    __tablename__ = "task_locks"

    id = Column(
        String,
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # One lock per audio file at a time
    audio_id = Column(
        String,
        ForeignKey("audio_files.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    locked_by = Column(
        String,
        ForeignKey("users.id"),
        nullable=False,
    )

    # Identifies which device/session holds the lock.
    # Used so same-user, different-device is also blocked.
    session_id = Column(
        String,
        nullable=False,
    )

    locked_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    # Extended by heartbeat. Expires if no heartbeat received.
    expires_at = Column(
        DateTime,
        nullable=False,
    )

    audio = relationship(
        "AudioFile",
        back_populates="task_lock",
    )

    locker = relationship("User")


# ──────────────────────────────────────────────────────────────────────────────
# SuperAdminAuditLog  (Phase 2 — immutable audit trail for Super Admin actions)
# ──────────────────────────────────────────────────────────────────────────────

class SuperAdminAuditLog(Base):
    """
    Immutable audit log for Super Admin actions.

    Unlike AuditLog (which tracks annotation workflow events),
    this table captures system-level administrative actions.

    Immutability guarantee:
    - No UPDATE or DELETE is ever issued against this table in code.
    - In production, the Supabase service role revokes DELETE on this table.
    - All writes use INSERT only.
    """
    __tablename__ = "super_admin_audit_logs"

    id = Column(
        String,
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # Who performed the action
    actor_id = Column(
        String,
        ForeignKey("users.id"),
        nullable=False,
    )

    # Who was affected (optional — for user management actions)
    target_user_id = Column(
        String,
        ForeignKey("users.id"),
        nullable=True,
    )

    action = Column(
        Enum(AuditAction),
        nullable=False,
    )

    # Human-readable description
    description = Column(
        Text,
        nullable=False,
    )

    # JSON blob with previous state (for rollback reference)
    previous_value = Column(
        Text,
        nullable=True,
    )

    # JSON blob with new state
    new_value = Column(
        Text,
        nullable=True,
    )

    # Client IP address
    ip_address = Column(
        String,
        nullable=True,
    )

    # Session identifier
    session_id = Column(
        String,
        nullable=True,
    )

    # Optional: reason provided by the admin
    reason = Column(
        Text,
        nullable=True,
    )

    # Timestamp — set once at insert, never updated
    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    actor = relationship("User", foreign_keys=[actor_id])
    target_user = relationship("User", foreign_keys=[target_user_id])

class SystemSettings(Base):
    __tablename__ = "system_settings"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    maintenance_mode = Column(Boolean, default=False, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
