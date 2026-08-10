"""
audio_utils.py – Audio metadata helpers.

Computes actual duration from audio files using mutagen (supports mp3, wav,
ogg, flac, m4a, etc.). Falls back to stdlib wave for .wav if mutagen fails.
"""

import wave
import contextlib
from pathlib import Path

from utils.logger import logger


def get_audio_duration(file_path: str) -> float:
    """
    Return the duration of an audio file in seconds.
    Returns 0.0 if the file cannot be read or does not exist.
    """
    p = Path(file_path)
    if not p.exists():
        return 0.0

    # --- Try mutagen first (supports mp3, ogg, flac, m4a, wav …) ---
    try:
        from mutagen import File as MutagenFile
        audio = MutagenFile(str(p))
        if audio is not None and audio.info is not None:
            return float(audio.info.length)
    except Exception:
        pass  # fall through to wave fallback

    # --- Stdlib wave fallback for uncompressed .wav ---
    if p.suffix.lower() == ".wav":
        try:
            with contextlib.closing(wave.open(str(p), "r")) as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
                if rate > 0:
                    return frames / float(rate)
        except Exception:
            pass

    logger.warning(f"Could not determine duration for: {file_path}")
    return 0.0
