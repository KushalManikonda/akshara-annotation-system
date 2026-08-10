"""
backend/api/health.py
---------------------
Health check endpoint.
Used by deployment platforms (Render) to verify the service is alive.
"""

from datetime import datetime, timezone

from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["Health"])


@router.get("/health", summary="Health check")
async def health_check():
    """
    Returns service status, version, and current UTC timestamp.
    No authentication required.
    """
    from backend.core.config import settings

    return {
        "status": "ok",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
