from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class AudioFileResponse(BaseModel):
    id: str
    dataset_id: str
    filename: str
    original_filename: str
    file_path: str
    audio_url: Optional[str] = None
    language: str
    original_transcript: Optional[str] = None
    english_translation: Optional[str] = None
    metadata_json: Optional[str] = None
    duration: Optional[float] = None
    status: str
    uploaded_by: str
    assigned_to: Optional[str] = None
    uploaded_at: datetime
    reviewed_count: Optional[int] = 0
    total_reviewers: Optional[int] = 0
    reviewed_by_me: Optional[bool] = False
    my_review_status: Optional[str] = None
    last_reviewer_comment: Optional[str] = None
    last_returned_at: Optional[datetime] = None
    submitted_at: Optional[datetime] = None
    annotator_username: Optional[str] = None
    dataset_name: Optional[str] = None

    class Config:
        from_attributes = True

class AudioStatusUpdate(BaseModel):
    status: str
