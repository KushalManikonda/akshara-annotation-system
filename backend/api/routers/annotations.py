from fastapi import APIRouter, Depends, HTTPException
from typing import List
from sqlalchemy.orm import Session
from backend.core.dependencies import get_current_user, get_db
from backend.schemas.annotation import AnnotationResponse, AnnotationCreate, ReviewCreate, AnnotationVersionResponse, RestoreVersionResponse, ProcessRsmlRequest
from database.models import User
from services.annotation_service import save_annotation, get_annotation_versions, restore_annotation_version, process_transcript
from services.reviewer_service import approve, add_comment

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
    from services.annotation_service import get_annotation
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
    from database.models import AudioFile, Annotation
    from database.enums import AnnotationState

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
    from services.annotation_service import get_annotation, submit_annotation
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
    from services.reviewer_service import get_annotation_for_task
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
    from database.models import AudioFile, Annotation
    from database.enums import AudioStatus, AnnotationState

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
        if audio.file_path and os.path.exists(audio.file_path):
            with open(audio.file_path, "rb") as f:
                zip_file.writestr(f"{stem}{audio_ext}", f.read())
        else:
            zip_file.writestr(f"{stem}{audio_ext}", b"")

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
