"""
backend/pipelines/pipeline_runner.py
--------------------------------------
Common dispatch interface for all three ASR pipelines.

Usage:
    from backend.pipelines.pipeline_runner import run_pipeline
    segments = run_pipeline("hindi", "/path/to/audio.wav")

Returns [{start, end, text}] or raises RuntimeError.
"""

import logging
from typing import List, Dict

logger = logging.getLogger("akshara.pipeline.runner")

SUPPORTED_LANGUAGES = ("hindi", "english", "telugu")


def run_pipeline(language: str, audio_path: str) -> List[Dict]:
    """
    Dispatch to the correct ASR pipeline based on language.

    Args:
        language: One of "hindi", "english", "telugu" (case-insensitive).
        audio_path: Absolute path to the original audio file.

    Returns:
        List of {start: float, end: float, text: str} dicts.

    Raises:
        ValueError: If language is not supported.
        RuntimeError: If the pipeline fails.
    """
    lang = language.lower().strip()

    if lang not in SUPPORTED_LANGUAGES:
        raise ValueError(
            f"Unsupported language '{language}'. "
            f"Supported: {', '.join(SUPPORTED_LANGUAGES)}"
        )

    logger.info(f"Pipeline runner: starting {lang} pipeline for {audio_path}")

    if lang == "english":
        from backend.pipelines.english_pipeline import run
    elif lang == "hindi":
        from backend.pipelines.hindi_pipeline import run
    elif lang == "telugu":
        from backend.pipelines.telugu_pipeline import run

    result = run(audio_path)
    logger.info(f"Pipeline runner: {lang} pipeline completed, {len(result)} segments")
    return result
