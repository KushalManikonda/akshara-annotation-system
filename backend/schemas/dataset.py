from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class MappedFileItem(BaseModel):
    audio_filename: str
    transcript_filename: str
    duration: float = 0.0

class DatasetResponse(BaseModel):
    id: str
    name: str
    zip_filename: str
    language: str
    uploaded_by: str
    uploader_username: Optional[str] = None
    total_files: int
    total_size: float
    total_duration: float
    uploaded_at: datetime
    mapped_files: List[MappedFileItem] = []

    class Config:
        from_attributes = True
