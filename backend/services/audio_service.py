import os
import re
import shutil
import uuid
import wave
import zipfile

from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.database.database import SessionLocal
from backend.database.models import AudioFile, Dataset, Annotation
from backend.database.enums import AudioStatus
from backend.utils.logger import logger
from backend.utils.metadata_parser import parse_metadata_from_extraction

from supabase import create_client, Client

# ==========================================================
# Storage
# ==========================================================

from backend.core.config import settings

BASE_AUDIO_PATH = settings.BASE_AUDIO_PATH
SUPABASE_URL = settings.SUPABASE_URL
SUPABASE_SERVICE_KEY = settings.SUPABASE_SERVICE_KEY
STORAGE_BUCKET = settings.STORAGE_BUCKET

supabase: Optional[Client] = None
if SUPABASE_URL and SUPABASE_SERVICE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# ==========================================================
# Database Session
# ==========================================================

def get_db() -> Session:
    return SessionLocal()


# ==========================================================
# Get All Audio
# ==========================================================

def get_all_audio() -> list[AudioFile]:

    db = get_db()

    try:
        return (
            db.query(AudioFile)
            .order_by(AudioFile.id.desc())
            .all()
        )

    finally:
        db.close()

def get_all_datasets():

    db = get_db()

    try:
        return (
            db.query(Dataset)
            .order_by(Dataset.uploaded_at.desc())
            .all()
        )

    finally:
        db.close()

def get_dataset_files(dataset_id: str):

    db = get_db()

    try:
        return (
            db.query(AudioFile)
            .filter(AudioFile.dataset_id == dataset_id)
            .order_by(AudioFile.original_filename)
            .all()
        )

    finally:
        db.close()
        
# ==========================================================
# Get Audio By ID
# ==========================================================

def get_audio_by_id(audio_id: str) -> Optional[AudioFile]:

    db = get_db()

    try:
        return (
            db.query(AudioFile)
            .filter(AudioFile.id == audio_id)
            .first()
        )

    finally:
        db.close()


# ==========================================================
# Audio Duration Helper
# ==========================================================

def _get_audio_duration(file_path: Path) -> float:
    """Return duration in seconds for the given audio file.
    Uses the built-in `wave` module for WAV files.
    Falls back to 0.0 if the file cannot be read.
    """
    try:
        ext = file_path.suffix.lower()
        if ext == ".wav":
            with wave.open(str(file_path), "rb") as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
                return frames / float(rate) if rate else 0.0
        # For MP3/FLAC etc., attempt mutagen if available
        try:
            from mutagen import File as MutagenFile
            audio = MutagenFile(str(file_path))
            if audio and audio.info:
                return audio.info.length
        except Exception:
            pass
        return 0.0
    except Exception:
        return 0.0


def _extract_id_from_path(p: Path) -> str:
    stem = p.stem  # e.g., 'lecture1', 'transcript1', 'lecture_01', 'clip1'
    digits = re.findall(r'\d+', stem)
    if digits:
        return digits[-1]
    norm = re.sub(r'^(lecture|transcript|audio|clip|segment)[_\-\s]*', '', stem, flags=re.IGNORECASE)
    return norm.strip().lower() if norm.strip() else stem.lower()


# ==========================================================
# Upload Audio
# ==========================================================

def upload_audio(uploaded_file, language: str, uploaded_by: str, extra_transcript_files: Optional[list] = None):
    """
    Upload a dataset ZIP file containing audio files and corresponding transcript JSON files.
    Optionally accepts extra transcript JSON files uploaded alongside the ZIP file.
    Audio and transcript files are linked deterministically using ID matching (e.g. lecture1.wav -> transcript1.json).
    Returns (success: bool, message: str) or bool.
    """
    db = get_db()

    try:

        # --------------------------------------------
        # Verify ZIP
        # --------------------------------------------
        
        try:
            with zipfile.ZipFile(uploaded_file, "r") as zip_ref:
                if zip_ref.testzip() is not None:
                    return False, "Invalid or corrupted ZIP archive."
        except zipfile.BadZipFile:
            return False, "Uploaded file is not a valid ZIP archive."
            
        uploaded_file.seek(0)

        # --------------------------------------------
        # Create Dataset
        # --------------------------------------------

        dataset_name = Path(uploaded_file.name).stem

        dataset = Dataset(
            name=dataset_name,
            zip_filename=uploaded_file.name,
            language=language,
            uploaded_by=uploaded_by,
            total_files=0,
            total_size=0.0,
            total_duration=0.0,
        )

        db.add(dataset)
        db.flush()

        # --------------------------------------------
        # Dataset Folder
        # --------------------------------------------

        dataset_folder = Path(BASE_AUDIO_PATH) / dataset.id
        dataset_folder.mkdir(parents=True, exist_ok=True)

        temp_zip = dataset_folder / uploaded_file.name

        with open(temp_zip, "wb") as f:
            shutil.copyfileobj(uploaded_file, f)

        # --------------------------------------------
        # Extract Files
        # --------------------------------------------

        extraction_dir = dataset_folder / "_extracted"
        extraction_dir.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(temp_zip, "r") as zip_ref:
            zip_ref.extractall(extraction_dir)

        children = list(extraction_dir.iterdir())
        if len(children) == 1 and children[0].is_dir():
            path_root = children[0]
        else:
            path_root = extraction_dir

        # Copy extra standalone transcript files if uploaded via UI form
        if extra_transcript_files:
            for tf in extra_transcript_files:
                tf_filename = getattr(tf, "name", getattr(tf, "filename", "transcript.json"))
                tf_dest = path_root / tf_filename
                try:
                    if hasattr(tf, "seek"):
                        tf.seek(0)
                    fileobj = getattr(tf, "_file", tf)
                    with open(tf_dest, "wb") as out_f:
                        shutil.copyfileobj(fileobj, out_f)
                except Exception as ex:
                    logger.warning(f"Failed to copy extra transcript file {tf_filename}: {ex}")

        # Parse metadata — pass the real root so metadata.csv is found there too
        metadata_map = parse_metadata_from_extraction(str(path_root))

        total_files = 0
        total_size = 0
        total_duration = 0.0

        audio_files_to_process = []
        json_transcript_files = []
        for extracted_file in path_root.rglob("*"):
            if not extracted_file.is_file():
                continue
            ext = extracted_file.suffix.lower()
            if ext in settings.SUPPORTED_AUDIO_FORMATS:
                audio_files_to_process.append(extracted_file)
            elif ext == ".json" and extracted_file.name.lower() not in ["metadata.json", "config.json"]:
                json_transcript_files.append(extracted_file)

        if not audio_files_to_process:
            return False, "No supported audio files found in ZIP archive."

        # ── Deterministic Audio <-> Transcript ID Mapping ──────────────────
        audio_map: dict[str, Path] = {}
        for af in audio_files_to_process:
            af_id = _extract_id_from_path(af)
            if af_id in audio_map:
                return False, f"Duplicate audio file ID '{af_id}' found: {af.name} and {audio_map[af_id].name}"
            audio_map[af_id] = af

        transcript_map: dict[str, Path] = {}
        for jf in json_transcript_files:
            jf_id = _extract_id_from_path(jf)
            if jf_id in transcript_map:
                return False, f"Duplicate transcript file ID '{jf_id}' found: {jf.name} and {transcript_map[jf_id].name}"
            transcript_map[jf_id] = jf

        # Validate 1-to-1 matching if separate transcript JSON files are present
        if transcript_map:
            audio_ids = set(audio_map.keys())
            transcript_ids = set(transcript_map.keys())
            missing_transcripts = audio_ids - transcript_ids
            if missing_transcripts:
                missing_str = ", ".join(sorted(missing_transcripts))
                return False, f"Missing corresponding transcript file for audio ID(s): {missing_str}"
            unmatched_transcripts = transcript_ids - audio_ids
            if unmatched_transcripts:
                unmatched_str = ", ".join(sorted(unmatched_transcripts))
                return False, f"Unmatched transcript file ID(s) without audio: {unmatched_str}"

        is_single_audio = len(audio_files_to_process) == 1

        for extracted_file in audio_files_to_process:
            extension = extracted_file.suffix.lower()

            unique_name = f"{uuid.uuid4()}{extension}"
            destination = dataset_folder / unique_name
            shutil.move(str(extracted_file), str(destination))

            size_mb = destination.stat().st_size / (1024 * 1024)

            # Full relative path from the real root, forward-slash normalised.
            # e.g. audio/102104052/3CnBuRhqnO4/clip_0001.mp3
            original_name = str(
                extracted_file.relative_to(path_root)
            ).replace("\\", "/")

            if is_single_audio and "_single_audio_" in metadata_map:
                meta = metadata_map["_single_audio_"]
            else:
                meta = metadata_map.get(original_name, {})

            # --------------------------------------------
            # Upload to Supabase Storage
            # --------------------------------------------
            # ── Upload to Supabase Storage ───────────────────────────────────
            audio_url = None
            if supabase:
                # Use a deterministic, portable storage key: dataset_id/filename
                # Store only the KEY (not full URL) so signed URL generation works correctly
                storage_key = f"{dataset.id}/{unique_name}"
                content_type = "audio/mpeg"
                if extension == ".wav": content_type = "audio/wav"
                elif extension == ".flac": content_type = "audio/flac"

                try:
                    with open(destination, "rb") as f:
                        supabase.storage.from_(STORAGE_BUCKET).upload(
                            path=storage_key,
                            file=f,
                            file_options={"content-type": content_type}
                        )
                    # Store the storage KEY (not full URL) — signed URLs are generated on demand
                    audio_url = storage_key
                    logger.info(f"Uploaded {storage_key} to Supabase Storage")
                except Exception as e:
                    logger.error(
                        f"Failed to upload {storage_key} to Supabase Storage: {e}. "
                        f"Task will use local audio model — annotators select WAV from their machine."
                    )
                    # Graceful fallback: audio_url stays None; task enters queue as local
                    audio_url = None


            af_id = _extract_id_from_path(extracted_file)
            transcript_content = None
            if af_id in transcript_map:
                try:
                    transcript_content = transcript_map[af_id].read_text(encoding="utf-8")
                except Exception as e:
                    logger.error(f"Error reading transcript file {transcript_map[af_id]}: {e}")

            if not transcript_content:
                transcript_content = meta.get("original_transcript")

            audio = AudioFile(

                dataset_id=dataset.id,

                filename=unique_name,

                original_filename=original_name,

                file_path=str(destination),

                audio_url=audio_url,

                # Phase 4+: mark storage type so frontend knows how to play
                audio_storage_type="supabase" if audio_url else "local",

                language=language,

                duration=_get_audio_duration(destination),

                status=AudioStatus.UNASSIGNED,

                uploaded_by=uploaded_by,

                assigned_to=None,

                original_transcript=transcript_content,

                english_translation=meta.get("english_translation"),

                metadata_json=meta.get("raw_metadata"),
            )

            db.add(audio)

            total_files += 1
            total_size += size_mb
            total_duration += audio.duration

        # Clean up extraction dir
        shutil.rmtree(extraction_dir, ignore_errors=True)

        # --------------------------------------------
        # Dataset Statistics
        # --------------------------------------------

        dataset.total_files = total_files
        dataset.total_size = round(total_size, 2)
        dataset.total_duration = round(total_duration, 2)

        db.commit()

        temp_zip.unlink(missing_ok=True)
        # Remove the local dataset folder since we fully rely on Supabase in production
        # In development, keep it for local file streaming.
        if getattr(settings, "ENVIRONMENT", "development") == "production":
            shutil.rmtree(dataset_folder, ignore_errors=True)

        return True

    except Exception:
        db.rollback()
        logger.exception("Audio upload failed")

        if 'dataset_folder' in locals() and dataset_folder.exists():
            shutil.rmtree(dataset_folder, ignore_errors=True)

        return False

    finally:

        db.close()


# ==========================================================
# Update Audio Status
# ==========================================================

def update_audio_status(audio_id: str, status: AudioStatus) -> bool:

    db = get_db()

    try:

        audio = (
            db.query(AudioFile)
            .filter(AudioFile.id == audio_id)
            .first()
        )

        if not audio:
            return False

        audio.status = status

        db.commit()

        return True

    except Exception:
        db.rollback()
        logger.exception(f"Failed to update audio status for {audio_id}")
        return False

    finally:
        db.close()


# ==========================================================
# Delete Audio
# ==========================================================

def delete_audio(audio_id: str) -> bool:

    db = get_db()

    try:

        audio = (
            db.query(AudioFile)
            .filter(AudioFile.id == audio_id)
            .first()
        )

        if not audio:
            return False

        # Delete related annotations first
        db.query(Annotation).filter(Annotation.audio_id == audio_id).delete(synchronize_session=False)

        if os.path.exists(audio.file_path):
            os.remove(audio.file_path)

        db.delete(audio)
        db.commit()

        return True

    except Exception:
        db.rollback()
        logger.exception(f"Failed to delete audio {audio_id}")
        return False

    finally:
        db.close()


# ==========================================================
# Delete Dataset
# ==========================================================

def delete_dataset(dataset_id: str) -> tuple[bool, str]:
    """
    Delete an entire dataset:
    - Deletes all Annotation rows for every audio file in the dataset.
    - Deletes all AudioFile rows.
    - Deletes the Dataset row.
    - Removes the on-disk folder (uuid-named folder under BASE_AUDIO_PATH).

    Returns:
        (True, "") on success, or (False, reason) on failure.
    """
    db = get_db()

    try:
        dataset = (
            db.query(Dataset)
            .filter(Dataset.id == dataset_id)
            .first()
        )

        if not dataset:
            return False, "Dataset not found."

        audio_files = (
            db.query(AudioFile)
            .filter(AudioFile.dataset_id == dataset_id)
            .all()
        )

        # Delete all annotations for every audio file first
        for audio in audio_files:
            db.query(Annotation).filter(
                Annotation.audio_id == audio.id
            ).delete(synchronize_session=False)

        # Delete all audio file rows
        for audio in audio_files:
            db.delete(audio)

        # Delete the dataset row
        db.delete(dataset)
        db.commit()

        # Remove files from disk — dataset folder is BASE_AUDIO_PATH / dataset_id
        dataset_folder = Path(BASE_AUDIO_PATH) / str(dataset_id)
        if dataset_folder.exists():
            shutil.rmtree(dataset_folder, ignore_errors=True)
            logger.info(f"Deleted dataset folder: {dataset_folder}")

        logger.info(
            f"Dataset {dataset_id} deleted: "
            f"{len(audio_files)} audio files removed."
        )

        return True, ""

    except Exception:
        db.rollback()
        logger.exception(f"Failed to delete dataset {dataset_id}")
        return False, "An unexpected error occurred. Check the logs."

    finally:
        db.close()


# ==========================================================
# Import Metadata for Existing Dataset
# ==========================================================

def get_csv_column_names(metadata_file) -> list:
    """
    Read only the header row of a CSV and return the column names.
    Used by the UI to let the admin map columns before importing.
    """
    import csv as _csv
    import io

    metadata_file.seek(0)
    content = metadata_file.read().decode("utf-8", errors="replace")
    metadata_file.seek(0)

    reader = _csv.DictReader(io.StringIO(content))
    return list(reader.fieldnames or [])


def import_metadata_for_dataset(
    dataset_id: str,
    metadata_file,
    filename_col: str = None,
    transcript_col: str = None,
    translation_col: str = None,
) -> tuple[int, int]:
    """
    Parse a standalone metadata.csv or metadata.json file and apply
    the transcript/translation data to AudioFile rows in an already-
    imported dataset.

    Args:
        dataset_id:      The ID of the target dataset.
        metadata_file:   A file-like object (e.g. from st.file_uploader).
        filename_col:    Column to use as the audio filename key (overrides auto-detect).
        transcript_col:  Column to use as the original transcript (overrides auto-detect).
        translation_col: Column to use as the English translation (overrides auto-detect).

    Returns:
        (matched_count, total_rows) so the caller can report coverage.
    """
    import tempfile
    from backend.utils.metadata_parser import parse_metadata_from_file

    db = get_db()

    try:
        suffix = Path(metadata_file.name).suffix.lower()

        with tempfile.TemporaryDirectory() as tmp_dir:
            dest_path = os.path.join(tmp_dir, "metadata" + suffix)
            metadata_file.seek(0)
            with open(dest_path, "wb") as f:
                f.write(metadata_file.read())

            metadata_map = parse_metadata_from_file(
                dest_path,
                filename_col=filename_col,
                transcript_col=transcript_col,
                translation_col=translation_col,
            )

        if not metadata_map:
            return 0, 0

        files = (
            db.query(AudioFile)
            .filter(AudioFile.dataset_id == dataset_id)
            .all()
        )

        matched = 0

        for audio in files:
            meta = metadata_map.get(audio.original_filename)
            if meta:
                audio.original_transcript = meta.get("original_transcript")
                audio.english_translation = meta.get("english_translation")
                audio.metadata_json = meta.get("raw_metadata")
                matched += 1

        db.commit()

        logger.info(
            f"Metadata import for dataset {dataset_id}: "
            f"{matched}/{len(files)} files matched."
        )

        return matched, len(metadata_map)

    except Exception:
        db.rollback()
        logger.exception(f"Failed to import metadata for dataset {dataset_id}")
        return 0, 0

    finally:
        db.close()