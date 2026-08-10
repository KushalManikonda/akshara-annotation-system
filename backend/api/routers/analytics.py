"""
backend/api/routers/analytics.py
---------------------------------
Analytics endpoints — Admin / Super Admin only.
Delegates all data aggregation to the existing analytics_service layer.
"""

from fastapi import APIRouter, Depends, HTTPException
from backend.core.dependencies import get_current_user
from database.models import User
from database.enums import UserRole
from services.analytics_service import (
    get_kpi_summary,
    get_pipeline_funnel,
    get_annotation_trend,
    get_dataset_breakdown,
    get_language_breakdown,
    get_annotator_leaderboard,
    get_reviewer_leaderboard,
    get_user_detail,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])

ADMIN_ROLES = {UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.PLATFORM}


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


@router.get("/global")
def global_stats(current_user: User = Depends(require_admin)):
    """High-level KPI summary for the platform."""
    return get_kpi_summary()


@router.get("/funnel")
def pipeline_funnel(current_user: User = Depends(require_admin)):
    """File counts at each pipeline stage (Unassigned → Reviewed)."""
    return get_pipeline_funnel()


@router.get("/trend")
def annotation_trend(days: int = 30, current_user: User = Depends(require_admin)):
    """Daily annotation submission counts for the past N days."""
    if days < 1 or days > 365:
        raise HTTPException(status_code=400, detail="days must be between 1 and 365")
    return get_annotation_trend(days=days)


@router.get("/datasets")
def dataset_breakdown(current_user: User = Depends(require_admin)):
    """Per-dataset completion breakdown."""
    return get_dataset_breakdown()


@router.get("/languages")
def language_breakdown(current_user: User = Depends(require_admin)):
    """File counts grouped by language."""
    return get_language_breakdown()


@router.get("/leaderboard/annotators")
def annotator_leaderboard(current_user: User = Depends(require_admin)):
    """Annotators ranked by approved task count."""
    return get_annotator_leaderboard()


@router.get("/leaderboard/reviewers")
def reviewer_leaderboard(current_user: User = Depends(require_admin)):
    """Reviewers ranked by total reviews completed."""
    return get_reviewer_leaderboard()


@router.get("/users/{user_id}")
def user_detail(user_id: str, current_user: User = Depends(require_admin)):
    """Detailed stats for a single user."""
    data = get_user_detail(user_id)
    if data is None:
        raise HTTPException(status_code=404, detail="User not found")
    return data
