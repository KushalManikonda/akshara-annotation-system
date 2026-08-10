from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from typing import List, Optional
from backend.core.dependencies import get_current_user
from backend.schemas.dataset import DatasetResponse
from backend.database.models import User
from backend.database.database import SessionLocal
from backend.database.models import Dataset, AudioFile, User
from backend.services.audio_service import get_all_datasets, delete_dataset, upload_audio, import_metadata_for_dataset, _extract_id_from_path
from pathlib import Path

router = APIRouter(prefix="/datasets", tags=["datasets"])

@router.get("/", response_model=List[DatasetResponse])
def read_datasets(current_user: User = Depends(get_current_user)):
    """
    Get all datasets with uploader username and mapped files.
    """
    db = SessionLocal()
    try:
        datasets = db.query(Dataset).order_by(Dataset.uploaded_at.desc()).all()
        results = []

        for ds in datasets:
            uploader = db.query(User).filter(User.id == ds.uploaded_by).first()
            uploader_username = uploader.username if uploader else "Admin"

            mapped_files = []
            audio_files = db.query(AudioFile).filter(AudioFile.dataset_id == ds.id).order_by(AudioFile.original_filename).all()
            for af in audio_files:
                af_stem = Path(af.original_filename).stem
                af_id = _extract_id_from_path(Path(af.original_filename))
                if "lecture" in af_stem.lower():
                    tf_name = f"transcript{af_id}.json"
                elif "_" in af_stem:
                    tf_name = f"transcript_{af_id}.json"
                else:
                    tf_name = f"transcript{af_id}.json"

                mapped_files.append({
                    "audio_filename": af.original_filename,
                    "transcript_filename": tf_name,
                    "duration": af.duration or 0.0
                })

            results.append(DatasetResponse(
                id=ds.id,
                name=ds.name,
                zip_filename=ds.zip_filename,
                language=ds.language,
                uploaded_by=ds.uploaded_by,
                uploader_username=uploader_username,
                total_files=ds.total_files,
                total_size=ds.total_size,
                total_duration=ds.total_duration,
                uploaded_at=ds.uploaded_at,
                mapped_files=mapped_files
            ))

        return results
    finally:
        db.close()

@router.delete("/{dataset_id}")
def remove_dataset(dataset_id: str, current_user: User = Depends(get_current_user)):
    """
    Delete a dataset and all associated audio/annotations.
    Requires SUPERADMIN role. (Role logic in service or dependencies)
    """
    role_val = current_user.role.value if hasattr(current_user.role, 'value') else current_user.role
    if role_val not in ["ADMIN", "SUPER_ADMIN"]:
        raise HTTPException(status_code=403, detail="Forbidden")

    success, msg = delete_dataset(dataset_id)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    
    return {"message": "Dataset deleted successfully"}

@router.post("/upload")
def upload_dataset(
    dataset_file: UploadFile = File(...),
    language: str = Form(...),
    meta_file: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_user)
):
    """
    Upload a dataset ZIP file and optionally a metadata CSV/JSON file.
    """
    role_val = current_user.role.value if hasattr(current_user.role, 'value') else current_user.role
    if role_val not in ["ADMIN", "SUPER_ADMIN"]:
        raise HTTPException(status_code=403, detail="Forbidden")

    # Wrap the SpooledTemporaryFile to mock Streamlit's UploadedFile 'name' property
    class FileWrapper:
        def __init__(self, file, name):
            self._file = file
            self.name = name
        def seekable(self): return True
        def readable(self): return True
        def writable(self): return False
        def __getattr__(self, item):
            return getattr(self._file, item)

    wrapped_dataset_file = FileWrapper(dataset_file.file, dataset_file.filename)

    res = upload_audio(wrapped_dataset_file, language, current_user.id)
    if isinstance(res, tuple):
        success, msg = res
    else:
        success, msg = res, "Upload failed. Check if it's a valid ZIP."

    if not success:
        raise HTTPException(status_code=400, detail=msg)

    if meta_file:
        wrapped_meta_file = FileWrapper(meta_file.file, meta_file.filename)
        # Fetch datasets, sort by uploaded_at descending to get the newly created dataset
        datasets = get_all_datasets()
        if datasets:
            new_dataset = datasets[0] # assuming get_all_datasets orders by newest first
            try:
                matched, total = import_metadata_for_dataset(
                    dataset_id=new_dataset.id,
                    metadata_file=wrapped_meta_file
                )
                return {"message": f"Dataset uploaded successfully. Metadata imported: {matched}/{total} matched."}
            except Exception as e:
                return {"message": f"Dataset uploaded, but metadata import failed: {str(e)}"}
            
    return {"message": "Dataset uploaded successfully."}
