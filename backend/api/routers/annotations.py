from fastapi import APIRouter, Depends, HTTPException
from typing import List
from sqlalchemy.orm import Session
import logging
from backend.core.dependencies import get_current_user, get_db
from backend.schemas.annotation import AnnotationResponse, AnnotationCreate, ReviewCreate, AnnotationVersionResponse, RestoreVersionResponse, ProcessRsmlRequest
from backend.database.models import User
from backend.services.annotation_service import save_annotation, get_annotation_versions, restore_annotation_version, process_transcript
from backend.services.reviewer_service import approve, add_comment
import os

logger = logging.getLogger("akshara.api")

router = APIRouter(prefix="/annotations", tags=["annotations"])

@router.post("/process-rsml")
def process_rsml(payload: ProcessRsmlRequest, current_user: User = Depends(get_current_user)):
    """
    Process an RSML transcript and return validation results, AST, and normalized string.
    """
    return process_transcript(payload.transcript)

@router.post("/")
def create_annotation(payload: AnnotationCreate, current_user: User = Depends(get_current_user)):
    """
    Save a new annotation.
    """
    from backend.services.annotation_service import get_annotation
    annotation = get_annotation(payload.audio_id, current_user.id)
    if not annotation:
        raise HTTPException(status_code=400, detail="Could not retrieve or create annotation for this task")
        
    success = save_annotation(
        annotation_id=annotation.id,
        transcript=payload.transcript,
        rsml=None
    )
    if not success:
        raise HTTPException(status_code=400, detail="Failed to save annotation")
    return {"message": "Annotation saved successfully"}

@router.get("/audio/{audio_id}", response_model=AnnotationResponse)
def get_annotation_by_audio(
    audio_id: str, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get the current annotation for a given audio task.
    """
    role_val = current_user.role.value if hasattr(current_user.role, "value") else current_user.role
    from backend.database.models import AudioFile, Annotation
    from backend.database.enums import AnnotationState

    annotation = db.query(Annotation).filter(Annotation.audio_id == audio_id).order_by(Annotation.updated_at.desc()).first()

    if not annotation:
        audio = db.query(AudioFile).filter(AudioFile.id == audio_id).first()
        if not audio:
            raise HTTPException(status_code=404, detail="Audio file not found")
        
        annotation = Annotation(
            audio_id=audio_id,
            annotator_id=audio.assigned_to or current_user.id,
            transcript=audio.original_transcript or "[]",
            state=AnnotationState.SUBMITTED if audio.status == "SUBMITTED" else AnnotationState.DRAFT
        )
        db.add(annotation)
        db.commit()
        db.refresh(annotation)
    
    # Check permissions
    if role_val == "ANNOTATOR":
        audio = db.query(AudioFile).filter(AudioFile.id == audio_id).first()
        if audio and audio.assigned_to != current_user.id:
            raise HTTPException(status_code=403, detail="You do not own this task")
        
    return annotation

@router.post("/{audio_id}/submit")
def submit_annotation_endpoint(audio_id: str, current_user: User = Depends(get_current_user)):
    """
    Submit an annotation (finalize draft, transition to SUBMITTED).
    """
    from backend.services.annotation_service import get_annotation, submit_annotation
    annotation = get_annotation(audio_id, current_user.id)
    if not annotation:
        raise HTTPException(status_code=404, detail="Annotation not found for this audio task")

    success = submit_annotation(annotation.id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to submit annotation")
    return {"message": "Annotation submitted successfully"}


@router.post("/review")
def create_review(payload: ReviewCreate, current_user: User = Depends(get_current_user)):
    """
    Save a review for an annotation.
    """
    if current_user.id != payload.reviewer_id:
         raise HTTPException(status_code=403, detail="Reviewer ID mismatch")

    # Assuming we need an annotation ID, but our ReviewCreate has audio_id?
    # Wait, reviewer_service requires annotation_id. 
    # Let's get the annotation_id from audio_id.
    from backend.services.reviewer_service import get_annotation_for_task
    annotation = get_annotation_for_task(payload.audio_id)
    if not annotation:
        raise HTTPException(status_code=404, detail="Annotation not found for this audio task")

    if payload.review_status == "APPROVED":
        success = approve(annotation.id, payload.reviewer_id)
        if not success:
            raise HTTPException(status_code=400, detail="Failed to save review")
    else:
        res = add_comment(annotation.id, payload.reviewer_id, payload.review_comments or "")
        if isinstance(res, tuple):
            success, msg = res
        else:
            success, msg = res, "Failed to return annotation"
        if not success:
            raise HTTPException(status_code=400, detail=msg)
    return {"message": "Review saved successfully"}

@router.get("/{audio_id}/versions", response_model=List[AnnotationVersionResponse])
def get_versions(audio_id: str, current_user: User = Depends(get_current_user)):
    """
    Get all versions of an annotation for a given audio task.
    """
    versions = get_annotation_versions(audio_id)
    return versions

@router.post("/{audio_id}/restore/{version_id}", response_model=RestoreVersionResponse)
def restore_version(audio_id: str, version_id: str, current_user: User = Depends(get_current_user)):
    """
    Restore an annotation to a previous version.
    """
    try:
        annotation = restore_annotation_version(audio_id, version_id, current_user.id)
        if not annotation:
            raise HTTPException(status_code=404, detail="Version or annotation not found")
        return RestoreVersionResponse(
            id=annotation.id,
            audio_id=annotation.audio_id,
            transcript=annotation.transcript or ""
        )
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/{audio_id}/export")
def export_annotation(
    audio_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Export fully approved annotation package containing:
    1. original audio (.wav)
    2. original transcript (.json)
    3. annotation work (.rsml)
    Only allowed for fully approved / COMPLETED annotations.
    """
    import io
    import zipfile
    from pathlib import Path
    from fastapi.responses import Response
    from backend.database.models import AudioFile, Annotation
    from backend.database.enums import AudioStatus, AnnotationState

    role_val = current_user.role.value if hasattr(current_user.role, "value") else current_user.role
    if role_val not in ("ADMIN", "SUPER_ADMIN"):
        raise HTTPException(status_code=403, detail="Admin access required to export annotations")

    audio = db.query(AudioFile).filter(AudioFile.id == audio_id).first()
    if not audio:
        raise HTTPException(status_code=404, detail="Audio file not found")

    annotation = db.query(Annotation).filter(Annotation.audio_id == audio_id).first()

    status_str = audio.status.value if hasattr(audio.status, "value") else str(audio.status)
    state_str = annotation.state.value if (annotation and hasattr(annotation.state, "value")) else str(annotation.state if annotation else "")

    is_approved = (status_str == "COMPLETED") and (state_str == "APPROVED")

    if not is_approved:
        raise HTTPException(
            status_code=400,
            detail="Only fully approved annotations in COMPLETED state can be exported."
        )

    stem = Path(audio.original_filename).stem if audio.original_filename else f"annotation_{audio_id}"
    audio_ext = Path(audio.original_filename).suffix or ".wav"

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        # 1. Original Audio
        audio_bytes = b""
        if audio.file_path and os.path.exists(audio.file_path):
            with open(audio.file_path, "rb") as f:
                audio_bytes = f.read()
        elif audio.audio_url:
            # For Supabase-hosted files, fetch via signed URL
            try:
                from backend.core.config import settings
                from supabase import create_client
                supa = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
                storage_key = audio.audio_url if not audio.audio_url.startswith("http") else "/".join(audio.audio_url.split("/")[-2:])
                signed_result = supa.storage.from_(settings.STORAGE_BUCKET).create_signed_url(
                    storage_key,
                    3600,
                )
                if isinstance(signed_result, dict):
                    signed_url = signed_result.get("signedURL") or signed_result.get("signedUrl") or signed_result.get("signed_url")
                else:
                    signed_url = signed_result
                if signed_url and signed_url.startswith("http"):
                    import urllib.request
                    with urllib.request.urlopen(signed_url) as resp:
                        audio_bytes = resp.read()
            except Exception as e:
                logger.warning(f"RSML export: could not fetch audio from Supabase for {audio_id}: {e}")

        zip_file.writestr(f"{stem}{audio_ext}", audio_bytes)

        # 2. Original Transcript JSON
        orig_transcript = audio.original_transcript or "{}"
        zip_file.writestr(f"{stem}.json", orig_transcript)

        # 3. Annotation Work RSML
        rsml_content = (annotation.rsml_content or annotation.transcript or "")
        zip_file.writestr(f"{stem}.rsml", rsml_content)

    zip_buffer.seek(0)
    return Response(
        content=zip_buffer.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={stem}_export.zip"}
    )


# ── SRT Export ────────────────────────────────────────────────────────────────

def _seconds_to_srt_timestamp(seconds: float) -> str:
    """
    Convert a float number of seconds to SRT timestamp format.
    SRT uses commas for milliseconds: HH:MM:SS,mmm
    """
    total_ms = int(round(seconds * 1000))
    ms = total_ms % 1000
    total_s = total_ms // 1000
    s = total_s % 60
    total_m = total_s // 60
    m = total_m % 60
    h = total_m // 60
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _build_srt(segments: list) -> str:
    """
    Build an SRT subtitle string from a list of {start, end, text} dicts.
    Uses UTF-8-safe string operations only. Caller must encode as UTF-8.
    """
    lines = []
    for i, seg in enumerate(segments, start=1):
        start_ts = _seconds_to_srt_timestamp(float(seg.get("start", 0)))
        end_ts = _seconds_to_srt_timestamp(float(seg.get("end", 0)))
        text = (seg.get("transcript") or seg.get("text") or "").strip()
        lines.append(str(i))
        lines.append(f"{start_ts} --> {end_ts}")
        lines.append(text)
        lines.append("")  # blank line between blocks
    return "\n".join(lines)


@router.get("/{audio_id}/export-srt")
def export_annotation_srt(
    audio_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Export a fully approved annotation as a ZIP archive containing:
      1. original_audio.wav  — the original uploaded WAV (not processed/denoised audio)
      2. original_transcript.json — the ASR-generated transcript before annotation
      3. annotated_transcript.srt — the final annotated transcript in SRT format

    SRT timestamps use comma for milliseconds (HH:MM:SS,mmm).
    Supports Hindi and Telugu Unicode characters via UTF-8 encoding.
    Only allowed for COMPLETED audio with APPROVED annotation state.
    Admin-only endpoint.
    """
    import io
    import json
    import zipfile
    from pathlib import Path
    from fastapi.responses import Response
    from backend.database.models import AudioFile, Annotation
    from backend.database.enums import AudioStatus, AnnotationState

    role_val = current_user.role.value if hasattr(current_user.role, "value") else current_user.role
    if role_val not in ("ADMIN", "SUPER_ADMIN"):
        raise HTTPException(status_code=403, detail="Admin access required to export annotations")

    audio = db.query(AudioFile).filter(AudioFile.id == audio_id).first()
    if not audio:
        raise HTTPException(status_code=404, detail="Audio file not found")

    # Get latest annotation (ordered by updated_at descending)
    annotation = (
        db.query(Annotation)
        .filter(Annotation.audio_id == audio_id)
        .order_by(Annotation.updated_at.desc())
        .first()
    )

    status_str = audio.status.value if hasattr(audio.status, "value") else str(audio.status)
    state_str = (
        annotation.state.value
        if (annotation and hasattr(annotation.state, "value"))
        else str(annotation.state if annotation else "")
    )

    is_approved = (status_str == "COMPLETED") and (state_str == "APPROVED")
    if not is_approved:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Only fully approved annotations can be exported as SRT. "
                f"Current state: audio={status_str}, annotation={state_str}"
            )
        )

    if not annotation:
        raise HTTPException(status_code=404, detail="No annotation found for this audio file")

    # ── Parse final annotated transcript ──────────────────────────────────────
    transcript_raw = annotation.transcript or "[]"
    try:
        segments = json.loads(transcript_raw)
        if not isinstance(segments, list):
            segments = []
    except Exception:
        segments = []

    # ── Build SRT content (UTF-8) ─────────────────────────────────────────────
    srt_content = _build_srt(segments)
    srt_bytes = srt_content.encode("utf-8")

    # ── Resolve original audio bytes ──────────────────────────────────────────
    audio_bytes = b""
    if audio.file_path and os.path.exists(audio.file_path):
        with open(audio.file_path, "rb") as f:
            audio_bytes = f.read()
    elif audio.audio_url:
        # For Supabase-hosted files, fetch via signed URL
        try:
            from backend.core.config import settings
            from supabase import create_client
            supa = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
            # audio_url is stored as a storage key (e.g. "dataset-id/filename.wav")
            # Legacy rows may have stored a full URL — extract the path from those
            storage_key = audio.audio_url if not audio.audio_url.startswith("http") else "/".join(audio.audio_url.split("/")[-2:])
            signed_result = supa.storage.from_(settings.STORAGE_BUCKET).create_signed_url(
                storage_key,
                3600,
            )
            if isinstance(signed_result, dict):
                signed_url = signed_result.get("signedURL") or signed_result.get("signedUrl") or signed_result.get("signed_url")
            else:
                signed_url = signed_result

            if signed_url and signed_url.startswith("http"):
                import urllib.request
                with urllib.request.urlopen(signed_url) as resp:
                    audio_bytes = resp.read()
        except Exception as e:
            logger.warning(f"SRT export: could not fetch audio from Supabase for {audio_id}: {e}")

    # ── Original transcript JSON (immutable) ──────────────────────────────────
    original_transcript_bytes = (audio.original_transcript or "[]").encode("utf-8")

    # ── Build ZIP ─────────────────────────────────────────────────────────────
    # Use a safe stem for the zip filename
    safe_stem = Path(audio.original_filename).stem if audio.original_filename else f"audio_{audio_id}"
    # Remove characters unsafe for filenames
    import re
    safe_stem = re.sub(r'[^\w\-_.]', '_', safe_stem)

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        # 1. Original audio (canonical WAV — not processed/denoised)
        zf.writestr("original_audio.wav", audio_bytes)

        # 2. Original transcript JSON (ASR output — immutable, never overwritten)
        zf.writestr("original_transcript.json", original_transcript_bytes)

        # 3. Annotated transcript in SRT format
        zf.writestr("annotated_transcript.srt", srt_bytes)

    zip_buffer.seek(0)
    zip_filename = f"export_{safe_stem}.zip"

    return Response(
        content=zip_buffer.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={zip_filename}"},
    )
