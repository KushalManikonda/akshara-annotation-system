import os
import sys
import json
import argparse
import logging
from pathlib import Path

# Add project root and streamlit_app to sys.path so we can import modules
project_root = Path(__file__).resolve().parent.parent
streamlit_app_path = project_root / "streamlit_app"
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(streamlit_app_path))

from streamlit_app.database.database import SessionLocal
from streamlit_app.database.models import AudioFile, Annotation
from streamlit_app.database.enums import AnnotationState

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("batch_importer")

def parse_args():
    parser = argparse.ArgumentParser(description="Batch import JSON transcripts into the database.")
    parser.add_argument("directory", help="Directory containing JSON transcript files.")
    parser.add_argument("--dry-run", action="store_true", help="Parse and match files without saving to the database.")
    return parser.parse_args()

def process_file(db, filepath: Path, dry_run: bool = False):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        logger.error(f"Failed to read/parse {filepath.name}: {e}")
        return False

    # Determine audio filename and segments
    audio_filename = None
    segments = None

    if isinstance(data, dict):
        # Format: {"audio_filename": "...", "segments": [...]}
        audio_filename = data.get("audio_filename")
        segments = data.get("segments") or data.get("transcript")
    elif isinstance(data, list):
        # Format: [...]
        segments = data
    else:
        logger.error(f"Unsupported JSON structure in {filepath.name}. Expected dict or list.")
        return False

    if not audio_filename:
        # Fallback to matching by file stem
        # e.g., 'clip_0001.json' -> look for 'clip_0001' in original_filename
        stem = filepath.stem
        audio_file = db.query(AudioFile).filter(
            AudioFile.original_filename.like(f"%{stem}%")
        ).first()
    else:
        audio_file = db.query(AudioFile).filter(
            AudioFile.original_filename == audio_filename
        ).first()
        if not audio_file:
            # Try wildcard matching
            stem = Path(audio_filename).stem
            audio_file = db.query(AudioFile).filter(
                AudioFile.original_filename.like(f"%{stem}%")
            ).first()

    if not audio_file:
        logger.error(f"Could not find matching AudioFile for {filepath.name} (searched for {audio_filename or filepath.stem})")
        return False

    if not segments or not isinstance(segments, list):
        logger.error(f"No valid segments found in {filepath.name}")
        return False

    transcript_str = json.dumps(segments)

    if dry_run:
        logger.info(f"[DRY RUN] Would update/create Annotation for Audio ID {audio_file.id} ({audio_file.original_filename})")
        return True

    try:
        # Check if annotation already exists
        annotation = db.query(Annotation).filter(Annotation.audio_id == audio_file.id).first()
        if annotation:
            # Avoid duplicate records by updating the existing one
            annotation.transcript = transcript_str
            annotation.state = AnnotationState.DRAFT
            logger.info(f"Updated existing Annotation (ID: {annotation.id}) for Audio ID {audio_file.id}")
        else:
            # Create a new annotation record (using the system or admin user as annotator, or None if acceptable)
            # Typically, imported transcripts are unassigned, but we can assign a dummy annotator or use uploaded_by
            annotator_id = audio_file.uploaded_by
            annotation = Annotation(
                audio_id=audio_file.id,
                annotator_id=annotator_id,
                transcript=transcript_str,
                state=AnnotationState.DRAFT
            )
            db.add(annotation)
            logger.info(f"Created new Annotation for Audio ID {audio_file.id}")
        
        db.commit()
        return True

    except Exception as e:
        db.rollback()
        logger.error(f"Database error while processing {filepath.name}: {e}")
        return False

def main():
    args = parse_args()
    directory = Path(args.directory)

    if not directory.is_dir():
        logger.error(f"Directory not found: {directory}")
        sys.exit(1)

    db = SessionLocal()
    success_count = 0
    failure_count = 0

    try:
        json_files = list(directory.glob("*.json"))
        if not json_files:
            logger.warning(f"No JSON files found in {directory}")
            return

        logger.info(f"Found {len(json_files)} JSON files. Starting import...")

        for filepath in json_files:
            success = process_file(db, filepath, dry_run=args.dry_run)
            if success:
                success_count += 1
            else:
                failure_count += 1

        logger.info(f"Batch import completed. Success: {success_count}, Failures: {failure_count}")

    finally:
        db.close()

if __name__ == "__main__":
    main()
