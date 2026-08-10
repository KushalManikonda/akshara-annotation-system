"""
backend/pipelines/hindi_pipeline.py
-------------------------------------
Hindi ASR pipeline.

Processing flow:
  Stage 1: SAM-Audio vocal separation (SamAudioInfer.from_pretrained("base", dtype="bfloat16"))
           Falls back to original audio if separation fails.
  Stage 2: Pyannote speaker diarization (pyannote/speaker-diarization-3.1)
           Requires HF_TOKEN environment variable.
           Produces speech timeline segments [{start, end}].
  Stage 3: AI4Bharat IndicConformer (ai4bharat/indic-conformer-600m-multilingual)
           Language code: "hi", mode: CTC
           Transcribes each speech segment from the vocal-separated audio.

Returns:
  [{start: float, end: float, text: str}]

The original uploaded audio file is NEVER modified.
Intermediate separated vocals are temporary and stored in PIPELINE_TEMP_DIR.
HF_TOKEN is read from environment — never from frontend/config.
"""

import logging
import os
import tempfile
from pathlib import Path
from typing import List, Dict

logger = logging.getLogger("akshara.pipeline.hindi")


def run(audio_path: str) -> List[Dict]:
    """
    Run the Hindi pipeline on the given audio file.

    Args:
        audio_path: Absolute path to the original audio file (WAV).

    Returns:
        List of {start: float, end: float, text: str} dicts.

    Raises:
        RuntimeError on pipeline failure.
    """
    hf_token = os.environ.get("HF_TOKEN", "")
    if not hf_token:
        raise RuntimeError(
            "HF_TOKEN environment variable is required for the Hindi pipeline (Pyannote diarization)."
        )

    temp_dir = os.environ.get("PIPELINE_TEMP_DIR", tempfile.gettempdir())
    os.makedirs(temp_dir, exist_ok=True)

    # ── Stage 1: SAM-Audio Vocal Separation ──────────────────────────────────
    vocals_path = _stage1_sam_separation(audio_path, temp_dir)

    # ── Stage 2: Pyannote Diarization ─────────────────────────────────────────
    speech_segments = _stage2_pyannote_diarization(vocals_path, hf_token)

    # ── Stage 3: IndicConformer Transcription ─────────────────────────────────
    transcript = _stage3_indic_conformer(vocals_path, speech_segments, language="hi")

    # Cleanup temporary vocals file
    try:
        if vocals_path != audio_path and os.path.exists(vocals_path):
            os.remove(vocals_path)
    except Exception as e:
        logger.warning(f"Hindi pipeline: could not clean up temp vocals: {e}")

    logger.info(f"Hindi pipeline: {len(transcript)} segments generated")
    return transcript


def _stage1_sam_separation(audio_path: str, temp_dir: str) -> str:
    """
    Use SAM-Audio to separate vocals from input audio.
    Returns path to vocals WAV (may be the original if separation fails).
    """
    vocals_out = os.path.join(temp_dir, f"hindi_vocals_{Path(audio_path).stem}.wav")

    try:
        from sam_audio import SamAudioInfer  # type: ignore
        import torch

        logger.info("Hindi pipeline Stage 1: SAM-Audio vocal separation")
        model = SamAudioInfer.from_pretrained("base", dtype="bfloat16")
        model.separate(audio_path, output_path=vocals_out)

        if os.path.exists(vocals_out):
            logger.info(f"Hindi pipeline Stage 1: vocals saved to {vocals_out}")
            return vocals_out
        else:
            logger.warning("Hindi pipeline Stage 1: separation succeeded but output not found; using original")
            return audio_path

    except Exception as e:
        logger.warning(f"Hindi pipeline Stage 1: SAM-Audio separation failed ({e}); falling back to original audio")
        return audio_path


def _stage2_pyannote_diarization(audio_path: str, hf_token: str) -> List[Dict]:
    """
    Run Pyannote speaker diarization to obtain speech timeline segments.
    Returns [{start: float, end: float}].
    """
    try:
        from pyannote.audio import Pipeline  # type: ignore
        import torch

        logger.info("Hindi pipeline Stage 2: Pyannote diarization")
        pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            use_auth_token=hf_token,
        )

        diarization = pipeline(audio_path)

        segments = []
        for turn, _, _ in diarization.itertracks(yield_label=True):
            segments.append({"start": round(turn.start, 3), "end": round(turn.end, 3)})

        # Merge overlapping/adjacent segments (within 0.3s gap)
        segments = _merge_segments(segments, gap_threshold=0.3)

        logger.info(f"Hindi pipeline Stage 2: {len(segments)} speech segments detected")
        return segments

    except Exception as e:
        raise RuntimeError(f"Hindi pipeline Stage 2: Pyannote diarization failed: {e}") from e


def _stage3_indic_conformer(audio_path: str, speech_segments: List[Dict], language: str = "hi") -> List[Dict]:
    """
    Transcribe each speech segment using AI4Bharat IndicConformer in CTC mode.
    Returns [{start, end, text}].
    """
    model_id = os.environ.get("INDIC_CONFORMER_MODEL", "ai4bharat/indic-conformer-600m-multilingual")

    try:
        from transformers import AutoProcessor, AutoModelForCTC  # type: ignore
        import torch
        import numpy as np

        logger.info(f"Hindi pipeline Stage 3: loading IndicConformer from {model_id}")
        processor = AutoProcessor.from_pretrained(model_id)
        model = AutoModelForCTC.from_pretrained(model_id)
        model.eval()

    except Exception as e:
        raise RuntimeError(f"Hindi pipeline Stage 3: failed to load IndicConformer ({model_id}): {e}") from e

    # Load full audio once
    from english_pipeline_utils import _load_audio_numpy  # local helper
    waveform, sample_rate = _load_audio_numpy(audio_path)

    transcript = []
    for seg in speech_segments:
        start_s = seg["start"]
        end_s = seg["end"]
        start_sample = int(start_s * sample_rate)
        end_sample = int(end_s * sample_rate)
        chunk = waveform[start_sample:end_sample]

        if len(chunk) < 100:
            continue

        try:
            import torch
            inputs = processor(
                chunk,
                sampling_rate=sample_rate,
                return_tensors="pt",
                language=language,
            )
            with torch.no_grad():
                logits = model(**inputs).logits
            predicted_ids = torch.argmax(logits, dim=-1)
            text = processor.decode(predicted_ids[0], skip_special_tokens=True).strip()
            if text:
                transcript.append({"start": round(start_s, 3), "end": round(end_s, 3), "text": text})
        except Exception as e:
            logger.warning(f"Hindi pipeline Stage 3: segment [{start_s}-{end_s}] failed: {e}")

    return transcript


def _merge_segments(segments: List[Dict], gap_threshold: float = 0.3) -> List[Dict]:
    """Merge speech segments that are within gap_threshold seconds of each other."""
    if not segments:
        return segments

    segments = sorted(segments, key=lambda s: s["start"])
    merged = [segments[0].copy()]

    for seg in segments[1:]:
        last = merged[-1]
        if seg["start"] - last["end"] <= gap_threshold:
            last["end"] = max(last["end"], seg["end"])
        else:
            merged.append(seg.copy())

    return merged


def _load_audio_numpy(audio_path: str):
    """
    Load audio file as mono float32 numpy array.
    Returns (waveform, sample_rate).
    """
    import numpy as np
    from pathlib import Path

    ext = Path(audio_path).suffix.lower()

    if ext == ".wav":
        import wave
        with wave.open(audio_path, "rb") as wf:
            n_channels = wf.getnchannels()
            sample_rate = wf.getframerate()
            n_frames = wf.getnframes()
            sample_width = wf.getsampwidth()
            raw = wf.readframes(n_frames)

        dtype_map = {1: np.int8, 2: np.int16, 4: np.int32}
        dtype = dtype_map.get(sample_width, np.int16)
        waveform = np.frombuffer(raw, dtype=dtype).astype(np.float32)
        max_val = float(2 ** (8 * sample_width - 1))
        waveform /= max_val
        if n_channels > 1:
            waveform = waveform.reshape(-1, n_channels).mean(axis=1)
        return waveform, sample_rate

    try:
        import soundfile as sf
        waveform, sr = sf.read(audio_path, always_2d=False)
        if waveform.ndim > 1:
            waveform = waveform.mean(axis=1)
        return waveform.astype(np.float32), sr
    except Exception:
        pass

    try:
        import librosa
        waveform, sr = librosa.load(audio_path, sr=None, mono=True)
        return waveform.astype(np.float32), sr
    except Exception as e:
        raise RuntimeError(f"Cannot load audio {audio_path}: {e}") from e
