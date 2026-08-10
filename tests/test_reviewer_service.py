import pytest
from services.reviewer_service import approve, add_comment
from database.models import User, AudioFile, Annotation, ReviewerApproval, Dataset
from database.enums import UserRole, AudioStatus, AnnotationState

def test_consensus_approval(db):
    rev1 = User(username="r1", email="r1@b.com", password_hash="h", role=UserRole.REVIEWER, is_active=True)
    rev2 = User(username="r2", email="r2@b.com", password_hash="h", role=UserRole.REVIEWER, is_active=True)
    annotator = User(username="a1", email="a1@b.com", password_hash="h", role=UserRole.ANNOTATOR, is_active=True)
    db.add_all([rev1, rev2, annotator])
    db.commit()

    dataset = Dataset(name="ds1", zip_filename="ds1.zip", language="eng", uploaded_by=annotator.id)
    db.add(dataset)
    db.commit()

    audio = AudioFile(filename="test.wav", original_filename="test.wav", file_path="path", language="eng", status=AudioStatus.SUBMITTED, assigned_to=annotator.id, duration=10.0, dataset_id=dataset.id)
    db.add(audio)
    db.commit()

    ann = Annotation(audio_id=audio.id, annotator_id=annotator.id, transcript="x", state=AnnotationState.SUBMITTED)
    db.add(ann)
    db.commit()

    approve(ann.id, rev1.id)
    db.refresh(ann)
    db.refresh(audio)
    
    assert ann.state == AnnotationState.SUBMITTED
    assert audio.status == AudioStatus.SUBMITTED
    
    approve(ann.id, rev2.id)
    db.refresh(ann)
    db.refresh(audio)
    
    assert ann.state == AnnotationState.APPROVED
    assert audio.status == AudioStatus.COMPLETED

def test_instant_return(db):
    rev1 = User(username="r3", email="r3@b.com", password_hash="h", role=UserRole.REVIEWER, is_active=True)
    rev2 = User(username="r4", email="r4@b.com", password_hash="h", role=UserRole.REVIEWER, is_active=True)
    annotator = User(username="a2", email="a2@b.com", password_hash="h", role=UserRole.ANNOTATOR, is_active=True)
    db.add_all([rev1, rev2, annotator])
    db.commit()

    dataset = Dataset(name="ds2", zip_filename="ds2.zip", language="eng", uploaded_by=annotator.id)
    db.add(dataset)
    db.commit()

    audio = AudioFile(filename="test2.wav", original_filename="test.wav", file_path="path", language="eng", status=AudioStatus.SUBMITTED, assigned_to=annotator.id, duration=10.0, dataset_id=dataset.id)
    db.add(audio)
    db.commit()

    ann = Annotation(audio_id=audio.id, annotator_id=annotator.id, transcript="x", state=AnnotationState.SUBMITTED)
    db.add(ann)
    db.commit()

    approve(ann.id, rev1.id)
    db.refresh(ann)
    assert ann.state == AnnotationState.SUBMITTED

    # Valid 10-word review comment
    success, msg = add_comment(ann.id, rev2.id, "The speaker boundary is incorrect and segment four needs correction.")
    assert success is True
    db.refresh(ann)
    db.refresh(audio)

    assert ann.state == AnnotationState.RETURNED
    assert audio.status == AudioStatus.REWORK_REQUIRED
    
    approvals = db.query(ReviewerApproval).filter(ReviewerApproval.annotation_id == ann.id, ReviewerApproval.is_valid == True).all()
    assert len(approvals) == 0
