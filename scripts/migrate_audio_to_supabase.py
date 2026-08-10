#!/usr/bin/env python3
"""
scripts/migrate_audio_to_supabase.py
------------------------------------
Uploads local audio files to Supabase Storage and updates the PostgreSQL database.

This script:
1. Connects to PostgreSQL and Supabase Storage.
2. Iterates over all audio files that don't have an `audio_url` yet.
3. Checks if the file exists on the local disk.
4. Uploads it to the `audio-files` bucket in Supabase.
5. Updates the `audio_url` in the database with the public URL.
"""

import os
import sys
from pathlib import Path

# Add streamlit_app to path
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_STREAMLIT_APP = os.path.join(_ROOT, "streamlit_app")
sys.path.insert(0, _STREAMLIT_APP)

from dotenv import load_dotenv
load_dotenv(os.path.join(_ROOT, ".env"))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from supabase import create_client, Client
from database.models import AudioFile

# Configure Supabase
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
STORAGE_BUCKET = os.environ.get("STORAGE_BUCKET", "audio-files")
DATABASE_URL = os.environ.get("DATABASE_URL")

if not all([SUPABASE_URL, SUPABASE_SERVICE_KEY, DATABASE_URL]):
    print("[ERROR] Missing required environment variables (.env).")
    sys.exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def get_content_type(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext == ".mp3":
        return "audio/mpeg"
    elif ext == ".wav":
        return "audio/wav"
    elif ext == ".flac":
        return "audio/flac"
    return "application/octet-stream"

def migrate():
    print(f"\n[INFO] Starting Audio Migration to Supabase bucket: {STORAGE_BUCKET}")
    db = SessionLocal()
    
    try:
        # Find files that need migration
        pending_files = db.query(AudioFile).filter(AudioFile.audio_url.is_(None)).all()
        total = len(pending_files)
        print(f"[INFO] Found {total} files pending migration in database.")
        
        if total == 0:
            print("[SUCCESS] All files are already migrated.")
            return

        success_count = 0
        missing_count = 0
        error_count = 0
        
        # In a real heavy-duty migration, we'd use ThreadPoolExecutor here,
        # but a sequential approach is safer for the first pass and avoids DB lock issues.
        for index, audio in enumerate(pending_files, 1):
            local_path = Path(_ROOT) / audio.file_path
            
            # 1. Verify local file exists
            if not local_path.exists():
                print(f"[{index}/{total}] [SKIP] Missing local file: {local_path}")
                missing_count += 1
                continue
            
            # 2. Upload to Supabase Storage
            # We'll use the UUID format from file_path to keep it unique in storage
            storage_path = str(Path(audio.file_path).as_posix())
            content_type = get_content_type(audio.filename)
            
            print(f"[{index}/{total}] Uploading {storage_path}...")
            try:
                with open(local_path, "rb") as f:
                    supabase.storage.from_(STORAGE_BUCKET).upload(
                        path=storage_path,
                        file=f,
                        file_options={"content-type": content_type}
                    )
                
                # 3. Get Public URL and update DB
                public_url = supabase.storage.from_(STORAGE_BUCKET).get_public_url(storage_path)
                audio.audio_url = public_url
                db.commit()
                success_count += 1
                
            except Exception as e:
                # If it already exists, just update the URL
                if "Duplicate" in str(e) or "already exists" in str(e).lower() or 'StatusCode.CONFLICT' in str(e):
                    print(f"  -> File already exists in storage, updating DB only.")
                    public_url = supabase.storage.from_(STORAGE_BUCKET).get_public_url(storage_path)
                    audio.audio_url = public_url
                    db.commit()
                    success_count += 1
                else:
                    print(f"  [ERROR] Upload failed for {storage_path}: {e}")
                    db.rollback()
                    error_count += 1

        print("\n========================================================")
        print("MIGRATION SUMMARY")
        print("========================================================")
        print(f"Total Pending: {total}")
        print(f"Successfully Migrated: {success_count}")
        print(f"Skipped (Missing Locally): {missing_count}")
        print(f"Failed (Errors): {error_count}")
        print("========================================================")

    finally:
        db.close()

if __name__ == "__main__":
    migrate()
