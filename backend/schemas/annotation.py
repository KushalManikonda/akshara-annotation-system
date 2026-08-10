from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class AnnotationResponse(BaseModel):
    id: str
    audio_id: str
    user_id: Optional[str] = None
    annotator_id: Optional[str] = None
    transcript: str
    time_taken: Optional[float] = 0.0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class AnnotationCreate(BaseModel):
    audio_id: str
    transcript: str
    time_taken: float = 0.0

class ReviewCreate(BaseModel):
    audio_id: str
    reviewer_id: str
    review_status: str
    review_comments: Optional[str] = None
    corrected_transcript: Optional[str] = None

class AnnotationVersionResponse(BaseModel):
    id: str
    annotation_id: str
    version_number: int
    transcript_snapshot: Optional[str]
    rsml_snapshot: Optional[str]
    submitted_by: str
    submitted_at: datetime
    
    class Config:
        from_attributes = True

class RestoreVersionResponse(BaseModel):
    id: str
    audio_id: str
    transcript: str

class ProcessRsmlRequest(BaseModel):
    transcript: str
