"""
backend/api/routers/curation.py
---------------------------------
Admin-only curation endpoints for the three-language ASR pipeline.

Endpoints:
  POST /curation/upload      - Upload original audio, create AudioFile record
  POST /curation/{id}/run    - Launch background ASR pipeline task
  GET  /curation/{id}/status - Poll pipeline processing status
  POST /curation/{id}/submit - Move completed transcript into annotation workflow

The pipeline status is stored in AudioFile.metadata_json (existing nullable field).
No schema migration required.

Status lifecycle (in metadata_json["pipeline_status"]):
  PENDING → PROCESSING → TRANSCRIBING → COMPLETED / FAILED

After /submit:
  - original_transcript is set from pipeline output
  - AudioFile.status → UNASSIGNED (enters existing annotation queue)
  - metadata_json pipeline keys are cleared
"""

import json
import logging
import os
import shutil
import uuid
import wave
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.core.dependencies import get_current_user, get_db
from backend.database.models import User, AudioFile, Dataset, AuditLog
from backend.database.enums import AudioStatus, AuditAction, UserRole

logger = logging.getLogger("akshara.curation")

router = APIRouter(prefix="/curation", tags=["curation"])

# ── Helpers ───────────────────────────────────────────────────────────────────

def _require_admin(current_user: User):
    role_val = current_user.role.value if hasattr(current_user.role, "value") else current_user.role
    if role_val not in ("ADMIN", "SUPER_ADMIN"):
        raise HTTPException(status_code=403, detail="Admin access required")


def _get_audio_or_404(audio_id: str, db: Session) -> AudioFile:
    audio = db.query(AudioFile).filter(AudioFile.id == audio_id).first()
    if not audio:
        raise HTTPException(status_code=404, detail="Audio file not found")
    return audio


def _get_duration_wav(file_path: str) -> float:
    try:
        with wave.open(file_path, "rb") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            return frames / float(rate) if rate else 0.0
    except Exception:
        return 0.0


def _get_or_create_curation_dataset(language: str, db: Session, uploader_id: str) -> Dataset:
    """
    Return (or lazily create) a special "Curation Pipeline" dataset for the given language.
    This groups pipeline-ingested audio files together without polluting user datasets.
    """
    ds_name = f"Pipeline: {language.capitalize()}"
    ds = db.query(Dataset).filter(Dataset.name == ds_name).first()
    if not ds:
        ds = Dataset(
            name=ds_name,
            zip_filename=f"pipeline_{language}.zip",
            language=language.capitalize(),
            uploaded_by=uploader_id,
            total_files=0,
            total_size=0.0,
            total_duration=0.0,
        )
        db.add(ds)
        db.flush()
    return ds


def _set_pipeline_meta(audio: AudioFile, db: Session, **kwargs):
    """
    Merge pipeline metadata into AudioFile.metadata_json without overwriting other keys.
    """
    try:
        existing = json.loads(audio.metadata_json) if audio.metadata_json else {}
    except Exception:
        existing = {}
    existing.update(kwargs)
    audio.metadata_json = json.dumps(existing, ensure_ascii=False)
    db.commit()


def _get_pipeline_meta(audio: AudioFile) -> dict:
    try:
        return json.loads(audio.metadata_json) if audio.metadata_json else {}
    except Exception:
        return {}


# ── Background Task ──────────────────────────────────────────────────────────

def _run_pipeline_background(audio_id: str, language: str, audio_file_path: str):
    """
    Called by FastAPI BackgroundTasks.
    Runs the ASR pipeline and persists results into AudioFile.metadata_json.
    """
    from backend.database.database import SessionLocal
    db = SessionLocal()
    try:
        audio = db.query(AudioFile).filter(AudioFile.id == audio_id).first()
        if not audio:
            logger.error(f"Curation: AudioFile {audio_id} not found at pipeline start")
            return

        _set_pipeline_meta(audio, db,
            pipeline_status="PROCESSING",
            pipeline_started_at=datetime.utcnow().isoformat(),
            pipeline_error=None,
        )

        logger.info(f"Curation: starting {language} pipeline for audio {audio_id}")

        # Update to TRANSCRIBING
        _set_pipeline_meta(audio, db, pipeline_status="TRANSCRIBING")

        from backend.pipelines.pipeline_runner import run_pipeline
        segments = run_pipeline(language, audio_file_path)

        transcript_json = json.dumps(segments, ensure_ascii=False)

        _set_pipeline_meta(audio, db,
            pipeline_status="COMPLETED",
            pipeline_transcript=transcript_json,
            pipeline_segments_count=len(segments),
            pipeline_completed_at=datetime.utcnow().isoformat(),
        )

        logger.info(f"Curation: pipeline COMPLETED for audio {audio_id}, {len(segments)} segments")

    except Exception as e:
        logger.exception(f"Curation: pipeline FAILED for audio {audio_id}: {e}")
        try:
            db.rollback()
            audio = db.query(AudioFile).filter(AudioFile.id == audio_id).first()
            if audio:
                _set_pipeline_meta(audio, db,
                    pipeline_status="FAILED",
                    pipeline_error=str(e),
                    pipeline_failed_at=datetime.utcnow().isoformat(),
                )
        except Exception:
            logger.exception("Curation: could not persist FAILED status")
    finally:
        db.close()
        # Clean up local file after pipeline finishes to prevent Render disk exhaustion
        if os.path.exists(audio_file_path):
            try:
                os.remove(audio_file_path)
            except Exception as e:
                logger.warning(f"Failed to clean up {audio_file_path}: {e}")


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/upload")
async def upload_original_audio(
    audio_file: UploadFile = File(...),
    language: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload the original audio file.
    Stores it as an AudioFile with pipeline_status=PENDING.
    Returns the audio_id for subsequent pipeline steps.

    The uploaded file is the CANONICAL original — it will appear in exports
    as original_audio.wav and is NEVER modified by the pipeline.
    """
    _require_admin(current_user)

    lang_clean = language.lower().strip()
    if lang_clean not in ("hindi", "english", "telugu"):
        raise HTTPException(status_code=400, detail="language must be 'hindi', 'english', or 'telugu'")

    # ── Determine storage path ────────────────────────────────────────────────
    from backend.core.config import settings

    from backend.core.config import settings
    BASE_AUDIO_PATH = settings.BASE_AUDIO_PATH

    # Get or create curation dataset
    ds = _get_or_create_curation_dataset(lang_clean, db, current_user.id)

    dataset_folder = Path(BASE_AUDIO_PATH) / ds.id
    dataset_folder.mkdir(parents=True, exist_ok=True)

    ext = Path(audio_file.filename or "audio.wav").suffix.lower() or ".wav"
    unique_name = f"{uuid.uuid4()}{ext}"
    dest_path = dataset_folder / unique_name

    # Write uploaded bytes to disk — this is the canonical original audio
    with open(dest_path, "wb") as f:
        content = await audio_file.read()
        f.write(content)

    # Get duration
    duration = _get_duration_wav(str(dest_path)) if ext == ".wav" else 0.0

    # ── Optionally upload to Supabase Storage ─────────────────────────────────
    audio_url = None
    if settings.SUPABASE_URL and settings.SUPABASE_SERVICE_KEY:
        try:
            from supabase import create_client
            supa = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
            storage_key = f"{ds.id}/{unique_name}"
            ct = "audio/wav" if ext == ".wav" else "audio/mpeg"
            with open(dest_path, "rb") as f:
                supa.storage.from_(settings.STORAGE_BUCKET).upload(
                    path=storage_key,
                    file=f,
                    file_options={"content-type": ct},
                )
            audio_url = supa.storage.from_(settings.STORAGE_BUCKET).get_public_url(storage_key)
        except Exception as e:
            logger.warning(f"Curation: Supabase upload failed (using local only): {e}")

    # ── Create AudioFile record ───────────────────────────────────────────────
    audio = AudioFile(
        dataset_id=ds.id,
        filename=unique_name,
        original_filename=audio_file.filename or unique_name,
        file_path=str(dest_path),
        audio_url=audio_url,
        language=lang_clean.capitalize(),
        duration=duration,
        status=AudioStatus.UNASSIGNED,  # will change once submitted to queue
        uploaded_by=current_user.id,
        assigned_to=None,
        original_transcript=None,  # filled after pipeline completes
        metadata_json=json.dumps({
            "pipeline_status": "PENDING",
            "pipeline_language": lang_clean,
            "original_audio_path": str(dest_path),
            "uploaded_at": datetime.utcnow().isoformat(),
        }, ensure_ascii=False),
    )
    db.add(audio)

    # Update dataset stats
    ds.total_files += 1
    ds.total_duration = round((ds.total_duration or 0.0) + duration, 2)

    db.commit()
    db.refresh(audio)

    logger.info(f"Curation: uploaded original audio {audio.id} ({audio_file.filename}) lang={lang_clean}")

    return {
        "audio_id": audio.id,
        "filename": audio.original_filename,
        "language": lang_clean,
        "duration": duration,
        "pipeline_status": "PENDING",
        "message": "Original audio stored. Call /run to start pipeline.",
    }


@router.post("/{audio_id}/run")
def run_pipeline(
    audio_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Launch the ASR pipeline as a background task.
    Returns immediately. Poll /status for progress.
    """
    _require_admin(current_user)
    audio = _get_audio_or_404(audio_id, db)

    meta = _get_pipeline_meta(audio)
    current_status = meta.get("pipeline_status", "")

    if current_status in ("PROCESSING", "TRANSCRIBING"):
        return {"message": "Pipeline is already running", "pipeline_status": current_status}

    if current_status == "COMPLETED":
        return {"message": "Pipeline already completed", "pipeline_status": "COMPLETED"}

    language = meta.get("pipeline_language", "")
    if not language:
        raise HTTPException(status_code=400, detail="No pipeline language set. Re-upload the audio.")

    audio_file_path = meta.get("original_audio_path") or audio.file_path
    if not audio_file_path or not os.path.exists(audio_file_path):
        raise HTTPException(status_code=404, detail=f"Original audio file not found at {audio_file_path}")

    # Set to PENDING before launching so the task picks up correctly
    _set_pipeline_meta(audio, db, pipeline_status="PENDING", pipeline_error=None)

    background_tasks.add_task(
        _run_pipeline_background,
        audio_id=audio_id,
        language=language,
        audio_file_path=audio_file_path,
    )

    logger.info(f"Curation: launched background pipeline for {audio_id} ({language})")
    return {"message": "Pipeline started", "pipeline_status": "PROCESSING", "audio_id": audio_id}


@router.get("/{audio_id}/status")
def get_pipeline_status(
    audio_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Poll the pipeline processing status for a given audio file.
    Returns status, segment count, and transcript preview.
    """
    _require_admin(current_user)
    audio = _get_audio_or_404(audio_id, db)
    meta = _get_pipeline_meta(audio)

    pipeline_status = meta.get("pipeline_status", "UNKNOWN")
    language = meta.get("pipeline_language", "")
    error = meta.get("pipeline_error")
    segments_count = meta.get("pipeline_segments_count", 0)
    transcript_json = meta.get("pipeline_transcript")

    # Parse transcript preview (first 5 segments)
    transcript_preview = []
    if transcript_json:
        try:
            segs = json.loads(transcript_json)
            transcript_preview = segs[:5]
        except Exception:
            pass

    return {
        "audio_id": audio_id,
        "filename": audio.original_filename,
        "language": language,
        "pipeline_status": pipeline_status,
        "segments_count": segments_count,
        "error": error,
        "transcript_preview": transcript_preview,
        "started_at": meta.get("pipeline_started_at"),
        "completed_at": meta.get("pipeline_completed_at"),
    }


@router.post("/{audio_id}/submit")
def submit_to_annotation_queue(
    audio_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Move a completed pipeline transcript into the existing annotation workflow.

    Steps:
    1. Copy pipeline_transcript → AudioFile.original_transcript
    2. Set AudioFile.status = UNASSIGNED (available in existing queue)
    3. Clear pipeline status keys from metadata_json
    4. Create an AuditLog entry

    After this, annotators can pick up the task from the existing queue exactly
    as they would for any other dataset upload.
    """
    _require_admin(current_user)
    audio = _get_audio_or_404(audio_id, db)
    meta = _get_pipeline_meta(audio)

    pipeline_status = meta.get("pipeline_status", "")
    if pipeline_status != "COMPLETED":
        raise HTTPException(
            status_code=400,
            detail=f"Pipeline must be COMPLETED before submitting. Current status: {pipeline_status}"
        )

    transcript_json = meta.get("pipeline_transcript")
    if not transcript_json:
        raise HTTPException(status_code=400, detail="No transcript found in pipeline output")

    # Persist the transcript as the canonical original transcript
    audio.original_transcript = transcript_json
    audio.status = AudioStatus.UNASSIGNED

    # Clean up pipeline-specific metadata but preserve language info
    preserved_meta = {
        "pipeline_language": meta.get("pipeline_language", ""),
        "pipeline_version": "1.0",
        "pipeline_submitted_at": datetime.utcnow().isoformat(),
        "original_audio_path": meta.get("original_audio_path", ""),
    }
    audio.metadata_json = json.dumps(preserved_meta, ensure_ascii=False)

    # Audit log
    audit = AuditLog(
        user_id=current_user.id,
        action=AuditAction.CREATE,
        details=(
            f"Curation pipeline submitted: audio {audio_id} ({audio.original_filename}) "
            f"[{meta.get('pipeline_language', '')}] added to annotation queue"
        ),
    )
    db.add(audit)
    db.commit()

    logger.info(f"Curation: audio {audio_id} submitted to annotation queue by {current_user.username}")

    return {
        "audio_id": audio_id,
        "message": "Transcript submitted to annotation queue successfully",
        "status": "UNASSIGNED",
    }


@router.get("/")
def list_curation_items(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all audio files that were ingested via the curation pipeline.
    Returns items that have pipeline metadata.
    """
    _require_admin(current_user)

    all_audio = db.query(AudioFile).all()
    results = []
    for audio in all_audio:
        meta = _get_pipeline_meta(audio)
        if "pipeline_status" in meta:
            results.append({
                "audio_id": audio.id,
                "filename": audio.original_filename,
                "language": meta.get("pipeline_language", audio.language),
                "pipeline_status": meta.get("pipeline_status", "UNKNOWN"),
                "status": audio.status.value if hasattr(audio.status, "value") else str(audio.status),
                "duration": audio.duration,
                "uploaded_at": audio.uploaded_at.isoformat() if audio.uploaded_at else None,
                "segments_count": meta.get("pipeline_segments_count", 0),
            })

    # Sort newest first
    results.sort(key=lambda r: r.get("uploaded_at") or "", reverse=True)
    return results
