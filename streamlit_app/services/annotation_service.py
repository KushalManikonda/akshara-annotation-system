from datetime import datetime

from sqlalchemy.orm import Session

from database.database import SessionLocal
from database.models import AudioFile, Annotation
from database.enums import AnnotationState, AudioStatus
from utils.logger import logger

from utils.rsml.tokenizer import tokenize
from utils.rsml.parser import RSMLParser
from utils.rsml.validator import RSMLValidator
from utils.rsml.normalizer import RSMLNormalizer

parser = RSMLParser()
validator = RSMLValidator()
normalizer = RSMLNormalizer()

def get_db() -> Session:
    return SessionLocal()


def get_tasks(annotator_id):

    db = get_db()

    try:
        return (
            db.query(AudioFile)
            .filter(AudioFile.assigned_to == annotator_id)
            .all()
        )

    finally:
        db.close()


def get_annotation(audio_id, annotator_id):

    db = get_db()

    try:
        annotation = (
            db.query(Annotation)
            .filter(
                Annotation.audio_id == audio_id,
                Annotation.annotator_id == annotator_id
            )
            .first()
        )

        if not annotation:
            audio = db.query(AudioFile).filter(AudioFile.id == audio_id).first()
            annotation = Annotation(
                audio_id=audio_id,
                annotator_id=annotator_id,
                transcript=audio.original_transcript if audio else None
            )

            db.add(annotation)
            db.commit()
            db.refresh(annotation)

        return annotation

    except Exception:
        db.rollback()
        logger.exception(f"Failed to get/create annotation for audio {audio_id}")
        return None

    finally:
        db.close()


def save_annotation(annotation_id, transcript, rsml):

    db = get_db()

    try:

        annotation = (
            db.query(Annotation)
            .filter(Annotation.id == annotation_id)
            .first()
        )

        if not annotation:
            return False

        if annotation.state == AnnotationState.APPROVED:
            raise ValueError("Cannot edit an annotation that is approved.")

        annotation.transcript = transcript
        annotation.rsml_content = rsml
        annotation.state = AnnotationState.DRAFT

        # Lifecycle: RESERVED (ASSIGNED) → IN_PROGRESS on first draft save
        audio = (
            db.query(AudioFile)
            .filter(AudioFile.id == annotation.audio_id)
            .first()
        )

        if audio and audio.status == AudioStatus.ASSIGNED:
            audio.status = AudioStatus.IN_PROGRESS
            logger.info(
                f"Audio {audio.id} transitioned ASSIGNED → IN_PROGRESS "
                f"(annotation {annotation_id})"
            )

        db.commit()

        return True

    except Exception:
        db.rollback()
        logger.exception(f"Failed to save annotation {annotation_id}")
        return False

    finally:
        db.close()



def submit_annotation(annotation_id):

    db = get_db()

    try:

        annotation = (
            db.query(Annotation)
            .filter(Annotation.id == annotation_id)
            .first()
        )

        if not annotation:
            return False

        if annotation.state == AnnotationState.APPROVED:
            raise ValueError("Cannot submit an annotation that is approved.")

        # ── Version Snapshot ──────────────────────────────────────────────────
        # Count existing versions so we can assign the next sequential number.
        from database.models import AnnotationVersion
        existing_count = (
            db.query(AnnotationVersion)
            .filter(AnnotationVersion.annotation_id == annotation_id)
            .count()
        )

        version = AnnotationVersion(
            annotation_id=annotation_id,
            version_number=existing_count + 1,
            transcript_snapshot=annotation.transcript,
            rsml_snapshot=annotation.rsml_content,
            submitted_by=annotation.annotator_id,
            submitted_at=datetime.utcnow(),
        )
        db.add(version)
        # ─────────────────────────────────────────────────────────────────────

        annotation.state = AnnotationState.SUBMITTED
        annotation.submitted_at = datetime.utcnow()

        audio = (
            db.query(AudioFile)
            .filter(AudioFile.id == annotation.audio_id)
            .first()
        )

        audio.status = AudioStatus.SUBMITTED

        db.commit()

        logger.info(
            f"Annotation {annotation_id} submitted as v{existing_count + 1}"
        )

        return True

    except Exception:
        db.rollback()
        logger.exception(f"Failed to submit annotation {annotation_id}")
        return False

    finally:
        db.close()


def process_transcript(transcript: str):
    """
    Process an RSML transcript and return all derived outputs.

    Returns:
        {
            "tokens": [...],
            "ast": [...],
            "messages": [...],
            "normalized": "..."
        }
    """

    tokens = tokenize(transcript)

    try:
        ast = parser.parse(tokens)
        messages = validator.validate(ast)
        normalized = normalizer.normalize(ast)
    except ValueError as e:
        from utils.rsml.validator import ValidationMessage
        ast = []
        messages = [ValidationMessage("ERROR", f"Syntax Error: {str(e)}")]
        normalized = ""

    return {
        "tokens": tokens,
        "ast": ast,
        "messages": messages,
        "normalized": normalized,
    }

def format_transcript(transcript: str) -> str:
    """
    Parses and reformats an RSML transcript for standard spacing.
    Returns the original transcript if there's a syntax error.
    """
    tokens = tokenize(transcript)
    try:
        ast = parser.parse(tokens)
        from utils.rsml.formatter import RSMLFormatter
        formatter = RSMLFormatter()
        return formatter.format(ast)
    except ValueError:
        # If parsing fails, just do basic space normalization
        import re
        return re.sub(r"\s+", " ", transcript).strip()

def get_annotation_versions(audio_id: str):
    db = get_db()
    try:
        from database.models import AnnotationVersion, Annotation
        annotation = db.query(Annotation).filter(Annotation.audio_id == audio_id).first()
        if not annotation:
            return []
        versions = db.query(AnnotationVersion).filter(AnnotationVersion.annotation_id == annotation.id).order_by(AnnotationVersion.version_number.desc()).all()
        return versions
    finally:
        db.close()

def restore_annotation_version(audio_id: str, version_id: str, current_user_id: str):
    db = get_db()
    try:
        from database.models import AnnotationVersion, Annotation
        annotation = db.query(Annotation).filter(Annotation.audio_id == audio_id).first()
        if not annotation:
            return None
        version = db.query(AnnotationVersion).filter(AnnotationVersion.id == version_id, AnnotationVersion.annotation_id == annotation.id).first()
        if not version:
            return None
        annotation.transcript = version.transcript_snapshot
        annotation.rsml_content = version.rsml_snapshot
        db.commit()
        db.refresh(annotation)
        return annotation
    finally:
        db.close()