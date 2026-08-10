"""
backend/pipelines/english_pipeline.py
--------------------------------------
English ASR pipeline using OpenAI Whisper.

Processing flow:
  1. Load source WAV (original, untouched)
  2. Convert stereo → mono if needed
  3. Resample to 16 kHz if needed
  4. Optional noise reduction (noisereduce)
  5. Process in 30-second chunks with WhisperForConditionalGeneration
  6. Convert local chunk timestamps → global lecture timestamps
  7. Return [{start, end, text}] transcript

Model location comes from WHISPER_MODEL_PATH env var (default: openai/whisper-base).
The original audio file is NEVER modified.
"""

import logging
import os
import tempfile
from pathlib import Path
from typing import List, Dict

logger = logging.getLogger("akshara.pipeline.english")

CHUNK_DURATION_S = 30  # 30-second chunks, as in the reference implementation
TARGET_SAMPLE_RATE = 16000


def run(audio_path: str) -> List[Dict]:
    """
    Run the English Whisper pipeline on the given audio file.

    Args:
        audio_path: Absolute path to the original WAV file.

    Returns:
        List of {start: float, end: float, text: str} dicts.

    Raises:
        RuntimeError on pipeline failure.
    """
    import numpy as np

    model_path = os.environ.get("WHISPER_MODEL_PATH", "openai/whisper-base")
    logger.info(f"English pipeline: loading Whisper from {model_path}")

    # ── Load & pre-process audio ──────────────────────────────────────────────
    waveform, sample_rate = _load_audio(audio_path)

    # Resample if needed
    if sample_rate != TARGET_SAMPLE_RATE:
        waveform = _resample(waveform, sample_rate, TARGET_SAMPLE_RATE)
        sample_rate = TARGET_SAMPLE_RATE

    # Optional noise reduction (non-destructive — original file unchanged)
    try:
        import noisereduce as nr
        waveform = nr.reduce_noise(y=waveform, sr=sample_rate).astype(np.float32)
        logger.info("English pipeline: noise reduction applied")
    except Exception as e:
        logger.warning(f"English pipeline: noise reduction skipped ({e})")

    # ── Load Whisper ──────────────────────────────────────────────────────────
    try:
        from transformers import WhisperProcessor, WhisperForConditionalGeneration
        processor = WhisperProcessor.from_pretrained(model_path)
        model = WhisperForConditionalGeneration.from_pretrained(model_path)
        model.eval()
    except Exception as e:
        raise RuntimeError(f"Failed to load Whisper model from {model_path}: {e}") from e

    forced_decoder_ids = processor.get_decoder_prompt_ids(language="en", task="transcribe")

    # ── Chunk processing ──────────────────────────────────────────────────────
    chunk_samples = CHUNK_DURATION_S * sample_rate
    total_samples = len(waveform)
    segments = []
    chunk_start = 0

    while chunk_start < total_samples:
        chunk_end = min(chunk_start + chunk_samples, total_samples)
        chunk = waveform[chunk_start:chunk_end]
        global_start_s = chunk_start / sample_rate
        global_end_s = chunk_end / sample_rate

        try:
            inputs = processor(
                chunk,
                sampling_rate=sample_rate,
                return_tensors="pt",
                return_attention_mask=True,
            )

            import torch
            with torch.no_grad():
                output = model.generate(
                    **inputs,
                    forced_decoder_ids=forced_decoder_ids,
                    return_timestamps=True,
                )

            # Decode with timestamps
            decoded = processor.decode(output[0], output_type="segments")

            if isinstance(decoded, dict) and "chunks" in decoded:
                # HF pipeline-style output
                for chunk_seg in decoded["chunks"]:
                    ts = chunk_seg.get("timestamp", (0.0, 0.0))
                    seg_start = (ts[0] or 0.0) + global_start_s
                    seg_end = (ts[1] or global_end_s - global_start_s) + global_start_s
                    text = chunk_seg.get("text", "").strip()
                    if text:
                        segments.append({"start": round(seg_start, 3), "end": round(seg_end, 3), "text": text})
            else:
                # Fallback: treat entire chunk as one segment
                text = processor.decode(output[0], skip_special_tokens=True).strip()
                if text:
                    segments.append({
                        "start": round(global_start_s, 3),
                        "end": round(global_end_s, 3),
                        "text": text,
                    })

        except Exception as e:
            logger.warning(f"English pipeline: chunk [{chunk_start}:{chunk_end}] failed: {e}")

        chunk_start = chunk_end

    logger.info(f"English pipeline: {len(segments)} segments generated")
    return segments


def _load_audio(audio_path: str):
    """Load audio as mono float32 numpy array. Returns (waveform, sample_rate)."""
    import numpy as np

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

        # Normalize to [-1, 1]
        max_val = float(2 ** (8 * sample_width - 1))
        waveform /= max_val

        # Mix to mono
        if n_channels > 1:
            waveform = waveform.reshape(-1, n_channels).mean(axis=1)

        return waveform, sample_rate

    # For non-WAV formats, try librosa/soundfile
    try:
        import soundfile as sf
        waveform, sample_rate = sf.read(audio_path, always_2d=False)
        if waveform.ndim > 1:
            waveform = waveform.mean(axis=1)
        return waveform.astype(np.float32), sample_rate
    except Exception:
        pass

    try:
        import librosa
        waveform, sample_rate = librosa.load(audio_path, sr=None, mono=True)
        return waveform.astype(np.float32), sample_rate
    except Exception as e:
        raise RuntimeError(f"Cannot load audio file {audio_path}: {e}") from e


def _resample(waveform, orig_sr: int, target_sr: int):
    """Resample waveform to target sample rate."""
    import numpy as np

    if orig_sr == target_sr:
        return waveform

    try:
        import librosa
        return librosa.resample(waveform, orig_sr=orig_sr, target_sr=target_sr)
    except Exception:
        pass

    try:
        from scipy.signal import resample_poly
        from math import gcd
        g = gcd(orig_sr, target_sr)
        return resample_poly(waveform, target_sr // g, orig_sr // g).astype(np.float32)
    except Exception as e:
        logger.warning(f"Resampling failed: {e}. Using original sample rate.")
        return waveform
