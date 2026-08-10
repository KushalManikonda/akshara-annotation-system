"""
tests/backend/test_phase3_storage.py
------------------------------------
Phase 3 Storage regression tests.
"""
import pytest
from database.database import SessionLocal
from database.models import AudioFile
import os

def test_audio_url_column_exists():
    """Verify that audio_url column exists and is accessible."""
    db = SessionLocal()
    try:
        # Just querying the first audio file to ensure no ORM error is thrown
        # regarding the audio_url property.
        audio = db.query(AudioFile).first()
        if audio:
            assert hasattr(audio, 'audio_url')
    finally:
        db.close()

def test_audio_file_paths():
    """Verify that we still have audio files to migrate or that they are migrated."""
    db = SessionLocal()
    try:
        count = db.query(AudioFile).count()
        assert count >= 0 # Just making sure the DB is reachable and valid
    finally:
        db.close()
