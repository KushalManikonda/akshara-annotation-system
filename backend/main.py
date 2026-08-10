"""
backend/main.py
---------------
FastAPI application entry point.
"""

import asyncio
import logging
import sys
import os
from datetime import datetime, timedelta

# ── Path setup ────────────────────────────────────────────────────────────────
# Services and Database are now correctly located in the backend/ package.
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("akshara.main")

# ── FastAPI ───────────────────────────────────────────────────────────────────
from fastapi import FastAPI
from backend.core.config import settings
from backend.core.middleware import configure_middleware
from backend.api.health import router as health_router
from backend.api.routers.users import router as users_router
from backend.api.routers.audio import router as audio_router
from backend.api.routers.datasets import router as datasets_router
from backend.api.routers.annotations import router as annotations_router
from backend.api.routers.auth import router as auth_router
from backend.api.routers.analytics import router as analytics_router
from backend.api.routers.queue import router as queue_router
from backend.api.routers.curation import router as curation_router

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
## Akshara Annotation Platform API

REST API for the Akshara multilingual speech annotation platform.

### Authentication
All endpoints (except `/api/health` and `/api/auth/login`) require a valid
JWT access token in the `Authorization: Bearer <token>` header.

### Roles
- **SUPER_ADMIN** — Full platform access
- **ADMIN** — Project management (datasets, users, assignments, analytics)
- **REVIEWER** — Review, approve, reject annotations
- **ANNOTATOR** — View and annotate assigned tasks
    """,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# ── Middleware ────────────────────────────────────────────────────────────────
configure_middleware(app)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(health_router)
app.include_router(auth_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(audio_router, prefix="/api")
app.include_router(datasets_router, prefix="/api")
app.include_router(annotations_router, prefix="/api")
app.include_router(analytics_router, prefix="/api")
app.include_router(queue_router, prefix="/api")
app.include_router(curation_router, prefix="/api")

from backend.api.routers.settings import router as settings_router
app.include_router(settings_router, prefix="/api")

# NOTE: Local static asset serving removed.
# All audio files are served from Supabase Storage via signed/public URLs.
# The /api/audio/{id}/stream endpoint redirects to Supabase Storage.


# ── Abandoned task cleanup ────────────────────────────────────────────────────

ASSIGNED_TIMEOUT_MINUTES = 20    # ASSIGNED but never opened
IN_PROGRESS_TIMEOUT_MINUTES = 45  # IN_PROGRESS with no heartbeat
CLEANUP_INTERVAL_SECONDS = 300    # Run every 5 minutes


async def _release_abandoned_tasks():
    """
    Background coroutine that runs every 5 minutes.
    Releases tasks back to UNASSIGNED if:
      - Status is ASSIGNED and assigned_at > 20 min ago (never opened)
      - Status is IN_PROGRESS and last_heartbeat_at > 45 min ago (tab closed / lost connection)
    Drafts are preserved — only task assignment status is rolled back.
    """
    from backend.database.database import SessionLocal
    from backend.database.models import AudioFile, AuditLog
    from backend.database.enums import AudioStatus, AuditAction

    while True:
        await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)
        db = SessionLocal()
        try:
            now = datetime.utcnow()
            released = 0

            # ── Release abandoned ASSIGNED tasks ──────────────────────────────
            assigned_cutoff = now - timedelta(minutes=ASSIGNED_TIMEOUT_MINUTES)
            abandoned_assigned = (
                db.query(AudioFile)
                .filter(
                    AudioFile.status == AudioStatus.ASSIGNED,
                    AudioFile.assigned_at <= assigned_cutoff,
                )
                .all()
            )
            for af in abandoned_assigned:
                old_assignee = af.assigned_to
                af.status = AudioStatus.UNASSIGNED
                af.assigned_to = None
                af.assigned_at = None
                af.last_heartbeat_at = None
                db.add(AuditLog(
                    user_id=old_assignee,
                    action=AuditAction.TASK_AUTO_RELEASED,
                    details=(
                        f"Task {af.id} ({af.original_filename}) auto-released "
                        f"after {ASSIGNED_TIMEOUT_MINUTES}min inactivity (ASSIGNED, never opened)"
                    ),
                ))
                released += 1

            # ── Release stale IN_PROGRESS tasks ──────────────────────────────
            progress_cutoff = now - timedelta(minutes=IN_PROGRESS_TIMEOUT_MINUTES)
            stale_progress = (
                db.query(AudioFile)
                .filter(
                    AudioFile.status == AudioStatus.IN_PROGRESS,
                    AudioFile.last_heartbeat_at <= progress_cutoff,
                )
                .all()
            )
            for af in stale_progress:
                old_assignee = af.assigned_to
                af.status = AudioStatus.UNASSIGNED
                af.assigned_to = None
                af.assigned_at = None
                af.last_heartbeat_at = None
                db.add(AuditLog(
                    user_id=old_assignee,
                    action=AuditAction.TASK_AUTO_RELEASED,
                    details=(
                        f"Task {af.id} ({af.original_filename}) auto-released "
                        f"after {IN_PROGRESS_TIMEOUT_MINUTES}min heartbeat timeout (IN_PROGRESS)"
                    ),
                ))
                released += 1

            if released > 0:
                db.commit()
                logger.info(f"Auto-released {released} abandoned task(s) back to UNASSIGNED")

        except Exception:
            logger.exception("Error during abandoned task cleanup")
            try:
                db.rollback()
            except Exception:
                pass
        finally:
            db.close()


# ── Startup / Shutdown ────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    
    # ── Database Diagnostic ───────────────────────────────────────────────
    logger.info("Database configuration loaded.")
    if settings.DATABASE_URL.startswith("postgresql"):
        logger.info("Database backend: PostgreSQL")
    else:
        logger.warning(f"Database backend: {settings.DATABASE_URL.split(':')[0]}")
        
    try:
        from backend.database.database import engine
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database connection: successful")
    except Exception as e:
        logger.error(f"CRITICAL: Database connection failed! {e}")
        sys.exit(1)
        
    logger.info("API docs available at /api/docs")
    # Launch the abandoned-task cleanup loop
    asyncio.create_task(_release_abandoned_tasks())
    logger.info(
        f"Abandoned task cleanup started "
        f"(ASSIGNED>{ASSIGNED_TIMEOUT_MINUTES}min, IN_PROGRESS>{IN_PROGRESS_TIMEOUT_MINUTES}min)"
    )


@app.on_event("shutdown")
async def shutdown():
    logger.info("Shutting down Akshara API")
