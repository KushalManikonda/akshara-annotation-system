import pytest
from services.annotation_service import save_annotation, submit_annotation
from database.models import User, AudioFile, Annotation, AnnotationVersion, Dataset
from database.enums import UserRole, AudioStatus, AnnotationState

def test_draft_saving(db):
    annotator = User(username="anno1", email="a@b.com", password_hash="hash", role=UserRole.ANNOTATOR)
    db.add(annotator)
    db.commit()

    dataset = Dataset(name="ds1", zip_filename="ds1.zip", language="eng", uploaded_by=annotator.id)
    db.add(dataset)
    db.commit()
    
    audio = AudioFile(filename="test.wav", original_filename="test.wav", file_path="path", language="eng", status=AudioStatus.ASSIGNED, assigned_to=annotator.id, duration=10.0, dataset_id=dataset.id)
    db.add(audio)
    db.commit()

    ann = Annotation(audio_id=audio.id, annotator_id=annotator.id, transcript="", state=AnnotationState.DRAFT)
    db.add(ann)
    db.commit()
    
    res = save_annotation(ann.id, "hello world", "")
    assert res is True
    
    db.refresh(ann)
    assert ann.transcript == "hello world"
    assert ann.state == AnnotationState.DRAFT

def test_submission_and_lock(db):
    annotator = User(username="anno2", email="a2@b.com", password_hash="hash", role=UserRole.ANNOTATOR)
    db.add(annotator)
    db.commit()

    dataset = Dataset(name="ds2", zip_filename="ds2.zip", language="eng", uploaded_by=annotator.id)
    db.add(dataset)
    db.commit()
    
    audio = AudioFile(filename="test2.wav", original_filename="test.wav", file_path="path", language="eng", status=AudioStatus.ASSIGNED, assigned_to=annotator.id, duration=10.0, dataset_id=dataset.id)
    db.add(audio)
    db.commit()

    ann = Annotation(audio_id=audio.id, annotator_id=annotator.id, transcript="final", state=AnnotationState.DRAFT)
    db.add(ann)
    db.commit()
    
    save_annotation(ann.id, "final_sub", "")
    res = submit_annotation(ann.id)
    assert res is True
    
    db.refresh(ann)
    db.refresh(audio)
    
    assert ann.state == AnnotationState.SUBMITTED
    assert audio.status == AudioStatus.SUBMITTED
    assert ann.transcript == "final_sub"
    
    versions = db.query(AnnotationVersion).filter(AnnotationVersion.annotation_id == ann.id).all()
    assert len(versions) == 1
    
    res_save = save_annotation(ann.id, "hack", "")
    assert res_save is False

    res_submit = submit_annotation(ann.id)
    assert res_submit is False
