"""
analytics_service.py
--------------------
All analytics queries for the Admin Dashboard (Phase 9).

Each function opens its own DB session, performs the query, closes the
session and returns plain Python data structures (dicts / lists of dicts)
so that the view layer never touches SQLAlchemy directly.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from database.database import SessionLocal
from database.models import (
    User,
    Dataset,
    AudioFile,
    Annotation,
    AnnotationVersion,
    ReviewerApproval,
    ReviewComment,
)
from database.enums import (
    UserRole,
    AudioStatus,
    AnnotationState,
    ApprovalStatus,
)
from sqlalchemy import func, case


# ─────────────────────────────────────────────────────────────────────────────
# 1. High-level KPI summary
# ─────────────────────────────────────────────────────────────────────────────

def get_kpi_summary() -> Dict[str, Any]:
    """
    Returns top-level platform-wide metrics:
        total_users, total_annotators, total_reviewers,
        total_audio, total_duration,
        approved_count, submitted_count, returned_count, draft_count,
        approved_duration, approved_pct
    """
    db = SessionLocal()
    try:
        total_users      = db.query(User).count()
        total_annotators = db.query(User).filter(User.role == UserRole.ANNOTATOR).count()
        total_reviewers  = db.query(User).filter(User.role == UserRole.REVIEWER).count()

        total_audio    = db.query(AudioFile).count()
        total_duration = db.query(func.sum(AudioFile.duration)).scalar() or 0.0

        state_counts = (
            db.query(Annotation.state, func.count(Annotation.id))
            .group_by(Annotation.state)
            .all()
        )
        counts = {s.value: c for s, c in state_counts}

        approved_count  = counts.get(AnnotationState.APPROVED, 0)
        submitted_count = counts.get(AnnotationState.SUBMITTED, 0)
        returned_count  = counts.get(AnnotationState.RETURNED, 0)
        draft_count     = counts.get(AnnotationState.DRAFT, 0)

        approved_duration = (
            db.query(func.sum(AudioFile.duration))
            .join(Annotation, Annotation.audio_id == AudioFile.id)
            .filter(Annotation.state == AnnotationState.APPROVED)
            .scalar() or 0.0
        )
        total_reviews = approved_count + returned_count
        approved_pct = (approved_count / total_reviews * 100) if total_reviews > 0 else 0.0

        total_datasets = db.query(Dataset).count()

        return {
            "total_users":       total_users,
            "total_annotators":  total_annotators,
            "total_reviewers":   total_reviewers,
            "total_datasets":    total_datasets,
            "total_audio":       total_audio,
            "total_duration":    total_duration,
            "approved_count":    approved_count,
            "submitted_count":   submitted_count,
            "returned_count":    returned_count,
            "draft_count":       draft_count,
            "approved_duration": approved_duration,
            "approved_pct":      approved_pct,
        }
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# 2. Pipeline funnel — file counts at each stage
# ─────────────────────────────────────────────────────────────────────────────

def get_pipeline_funnel() -> List[Dict[str, Any]]:
    """
    Returns an ordered list of pipeline stages with their counts:
        [{"stage": "UNASSIGNED", "count": N}, ...]
    """
    db = SessionLocal()
    try:
        # AudioFile status
        audio_counts = (
            db.query(AudioFile.status, func.count(AudioFile.id))
            .group_by(AudioFile.status)
            .all()
        )
        status_map = {s.value: c for s, c in audio_counts}

        ordered_stages = [
            AudioStatus.UNASSIGNED,
            AudioStatus.ASSIGNED,
            AudioStatus.IN_PROGRESS,
            AudioStatus.SUBMITTED,
            AudioStatus.REWORK_REQUIRED,
            AudioStatus.COMPLETED,
        ]

        return [
            {"stage": s.value, "count": status_map.get(s.value, 0)}
            for s in ordered_stages
        ]
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# 3. Annotation submission trend (daily, last N days)
# ─────────────────────────────────────────────────────────────────────────────

def get_annotation_trend(days: int = 30) -> List[Dict[str, Any]]:
    """
    Returns daily submission counts for the past `days` days.
    Each item: {"date": "YYYY-MM-DD", "submitted": N}
    Days with zero submissions are included.
    """
    db = SessionLocal()
    try:
        since = datetime.utcnow() - timedelta(days=days)

        rows = (
            db.query(
                func.date(AnnotationVersion.submitted_at).label("day"),
                func.count(AnnotationVersion.id).label("submitted"),
            )
            .filter(AnnotationVersion.submitted_at >= since)
            .group_by(func.date(AnnotationVersion.submitted_at))
            .order_by(func.date(AnnotationVersion.submitted_at))
            .all()
        )

        # Build a full date range with zeros for missing days
        date_map = {str(row.day): row.submitted for row in rows}
        result = []
        for i in range(days):
            d = (since + timedelta(days=i + 1)).strftime("%Y-%m-%d")
            result.append({"date": d, "submitted": date_map.get(d, 0)})

        return result
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# 4. Per-dataset breakdown
# ─────────────────────────────────────────────────────────────────────────────

def get_dataset_breakdown() -> List[Dict[str, Any]]:
    """
    Returns one row per dataset:
        name, language, total_files, total_duration,
        approved_files, approved_duration, approved_pct
    """
    db = SessionLocal()
    try:
        datasets = db.query(Dataset).order_by(Dataset.uploaded_at.desc()).all()
        result = []

        for ds in datasets:
            total_files    = db.query(AudioFile).filter(AudioFile.dataset_id == ds.id).count()
            total_duration = (
                db.query(func.sum(AudioFile.duration))
                .filter(AudioFile.dataset_id == ds.id)
                .scalar() or 0.0
            )

            approved_files = (
                db.query(AudioFile)
                .join(Annotation, Annotation.audio_id == AudioFile.id)
                .filter(AudioFile.dataset_id == ds.id)
                .filter(Annotation.state == AnnotationState.APPROVED)
                .count()
            )

            approved_duration = (
                db.query(func.sum(AudioFile.duration))
                .join(Annotation, Annotation.audio_id == AudioFile.id)
                .filter(AudioFile.dataset_id == ds.id)
                .filter(Annotation.state == AnnotationState.APPROVED)
                .scalar() or 0.0
            )

            approved_pct = (approved_files / total_files * 100) if total_files > 0 else 0.0

            result.append({
                "name":              ds.name,
                "language":          ds.language,
                "total_files":       total_files,
                "total_duration_s":  round(total_duration, 2),
                "approved_files":    approved_files,
                "approved_duration_s": round(approved_duration, 2),
                "approved_pct":      round(approved_pct, 1),
            })

        return result
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# 5. Language breakdown
# ─────────────────────────────────────────────────────────────────────────────

def get_language_breakdown() -> List[Dict[str, Any]]:
    """
    Returns one row per language code:
        language, file_count, total_duration_s
    """
    db = SessionLocal()
    try:
        rows = (
            db.query(
                AudioFile.language,
                func.count(AudioFile.id).label("file_count"),
                func.sum(AudioFile.duration).label("total_duration"),
            )
            .group_by(AudioFile.language)
            .order_by(func.count(AudioFile.id).desc())
            .all()
        )

        return [
            {
                "language":        row.language or "Unknown",
                "file_count":      row.file_count,
                "total_duration_s": round(row.total_duration or 0.0, 2),
            }
            for row in rows
        ]
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# 6. Annotator leaderboard
# ─────────────────────────────────────────────────────────────────────────────

def get_annotator_leaderboard() -> List[Dict[str, Any]]:
    """
    Returns annotators ranked by Quality percentage (approved / submitted * 100).
    Includes: username, total_assigned, submitted, approved, returned,
              approved_duration_s, quality_pct
    """
    db = SessionLocal()
    try:
        annotators = db.query(User).filter(User.role == UserRole.ANNOTATOR).all()
        result = []

        for user in annotators:
            annotations = (
                db.query(Annotation)
                .filter(Annotation.annotator_id == user.id)
                .all()
            )

            total_assigned = len(annotations)
            approved  = sum(1 for a in annotations if a.state == AnnotationState.APPROVED)
            
            # Count historical returns based on ReviewComments for this annotator's annotations
            annotation_ids = [a.id for a in annotations]
            returned = (
                db.query(func.count(ReviewComment.id))
                .filter(ReviewComment.annotation_id.in_(annotation_ids))
                .scalar() or 0
            ) if annotation_ids else 0
            
            under_review = sum(1 for a in annotations if a.state == AnnotationState.SUBMITTED)
            # Submitted tasks count = all tasks submitted (approved + returned + under_review)
            submitted_total = approved + returned + under_review

            quality_pct = (approved / submitted_total * 100.0) if submitted_total > 0 else 0.0

            approved_duration = (
                db.query(func.sum(AudioFile.duration))
                .join(Annotation, Annotation.audio_id == AudioFile.id)
                .filter(Annotation.annotator_id == user.id)
                .filter(Annotation.state == AnnotationState.APPROVED)
                .scalar() or 0.0
            )

            result.append({
                "username":           user.username,
                "total_assigned":     total_assigned,
                "submitted":          submitted_total,
                "approved":           approved,
                "returned":           returned,
                "quality_pct":        round(quality_pct, 1),
                "approved_duration_s": round(approved_duration, 2),
            })

        # Deterministic sort: Quality % desc, Approved desc, Submitted desc, username asc
        result.sort(key=lambda x: (x["quality_pct"], x["approved"], x["submitted"], -ord(x["username"][0]) if x["username"] else 0), reverse=True)
        return result
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# 7. Reviewer leaderboard
# ─────────────────────────────────────────────────────────────────────────────

def get_reviewer_leaderboard() -> List[Dict[str, Any]]:
    """
    Returns reviewers ranked by Quality percentage (approvals / total_reviews * 100).
    Includes: username, total_reviews, approvals, rejections, quality_pct
    """
    db = SessionLocal()
    try:
        reviewers = db.query(User).filter(User.role == UserRole.REVIEWER).all()
        result = []

        for user in reviewers:
            approved_count = (
                db.query(func.count(ReviewerApproval.id))
                .filter(
                    ReviewerApproval.reviewer_id == user.id,
                    ReviewerApproval.status == ApprovalStatus.APPROVED,
                    ReviewerApproval.is_valid == True
                )
                .scalar() or 0
            )

            rejected_count = (
                db.query(func.count(ReviewComment.id))
                .filter(ReviewComment.reviewer_id == user.id)
                .scalar() or 0
            )

            total_reviews = approved_count + rejected_count
            quality_pct = (approved_count / total_reviews * 100.0) if total_reviews > 0 else 0.0

            result.append({
                "username":      user.username,
                "total_reviews": total_reviews,
                "approvals":     approved_count,
                "rejections":    rejected_count,
                "quality_pct":   round(quality_pct, 1),
            })

        # Deterministic sort: Quality % desc, Approvals desc, Total reviews desc, username asc
        result.sort(key=lambda x: (x["quality_pct"], x["approvals"], x["total_reviews"], -ord(x["username"][0]) if x["username"] else 0), reverse=True)
        return result
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# 8. Per-user detail
# ─────────────────────────────────────────────────────────────────────────────

def get_user_detail(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Returns detailed stats for a single user (annotator or reviewer).
    """
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return None

        if user.role == UserRole.ANNOTATOR:
            annotations = (
                db.query(Annotation)
                .filter(Annotation.annotator_id == user.id)
                .order_by(Annotation.created_at.desc())
                .all()
            )

            recent = []
            for ann in annotations[:10]:
                audio = db.query(AudioFile).filter(AudioFile.id == ann.audio_id).first()
                recent.append({
                    "audio_filename": audio.original_filename if audio else "Unknown",
                    "state":          str(ann.state),
                    "submitted_at":   ann.submitted_at.strftime("%Y-%m-%d") if ann.submitted_at else "—",
                    "duration_s":     round(audio.duration or 0, 2) if audio else 0,
                })

            return {
                "role":           "ANNOTATOR",
                "username":       user.username,
                "email":          user.email,
                "joined":         user.created_at.strftime("%Y-%m-%d") if user.created_at else "—",
                "total_assigned": len(annotations),
                "approved":       sum(1 for a in annotations if a.state == AnnotationState.APPROVED),
                "submitted":      sum(1 for a in annotations if a.state == AnnotationState.SUBMITTED),
                "returned":       (
                    db.query(func.count(ReviewComment.id))
                    .filter(ReviewComment.annotation_id.in_([a.id for a in annotations]))
                    .scalar() or 0
                ) if annotations else 0,
                "draft":          sum(1 for a in annotations if a.state == AnnotationState.DRAFT),
                "recent_tasks":   recent,
            }

        elif user.role == UserRole.REVIEWER:
            approvals_count = (
                db.query(func.count(ReviewerApproval.id))
                .filter(
                    ReviewerApproval.reviewer_id == user.id,
                    ReviewerApproval.status == ApprovalStatus.APPROVED,
                    ReviewerApproval.is_valid == True
                )
                .scalar() or 0
            )

            rejections_count = (
                db.query(func.count(ReviewComment.id))
                .filter(ReviewComment.reviewer_id == user.id)
                .scalar() or 0
            )

            total_reviews = approvals_count + rejections_count

            return {
                "role":           "REVIEWER",
                "username":       user.username,
                "email":          user.email,
                "joined":         user.created_at.strftime("%Y-%m-%d") if user.created_at else "—",
                "total_reviews":  total_reviews,
                "approvals":      approvals_count,
                "rejections":     rejections_count,
                "recent_reviews": [],
            }

        else:
            return {
                "role":     "ADMIN",
                "username": user.username,
                "email":    user.email,
                "joined":   user.created_at.strftime("%Y-%m-%d") if user.created_at else "—",
            }
    finally:
        db.close()
