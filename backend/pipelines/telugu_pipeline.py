"""
backend/pipelines/telugu_pipeline.py
--------------------------------------
Telugu ASR pipeline.

Processing flow:
  Stage 1: Silero VAD — load_silero_vad() + get_speech_timestamps()
           Audio loaded as mono 16 kHz.
           Produces [{start, end}] in seconds.
  Stage 2: AI4Bharat IndicConformer (ai4bharat/indic-conformer-600m-multilingual)
           Language code: "te", mode: CTC
           For each VAD segment, transcribes the corresponding audio slice.

Returns:
  [{start: float, end: float, text: str}]

The original uploaded audio file is NEVER modified.
Intermediate timestamps are runtime-only (not persisted).
"""

import logging
import os
from pathlib import Path
from typing import List, Dict

logger = logging.getLogger("akshara.pipeline.telugu")

SILERO_SAMPLE_RATE = 16000


def run(audio_path: str) -> List[Dict]:
    """
    Run the Telugu pipeline on the given audio file.

    Args:
        audio_path: Absolute path to the original audio file (WAV).

    Returns:
        List of {start: float, end: float, text: str} dicts.

    Raises:
        RuntimeError on pipeline failure.
    """
    # ── Stage 1: Silero VAD ───────────────────────────────────────────────────
    waveform_16k, speech_segments = _stage1_silero_vad(audio_path)

    # ── Stage 2: IndicConformer Transcription ─────────────────────────────────
    transcript = _stage2_indic_conformer(waveform_16k, speech_segments, language="te")

    logger.info(f"Telugu pipeline: {len(transcript)} segments generated")
    return transcript


def _stage1_silero_vad(audio_path: str):
    """
    Load audio at 16 kHz mono and run Silero VAD.
    Returns (waveform_tensor_16k, [{start, end}] in seconds).
    """
    try:
        import torch
        from silero_vad import load_silero_vad, get_speech_timestamps  # type: ignore

        logger.info("Telugu pipeline Stage 1: Silero VAD")

        # Load and resample to 16 kHz mono
        waveform, sample_rate = _load_as_16k_mono_tensor(audio_path)

        vad_model = load_silero_vad()

        timestamps = get_speech_timestamps(
            waveform,
            vad_model,
            sampling_rate=SILERO_SAMPLE_RATE,
            return_seconds=True,
        )

        # Convert to [{start, end}] — timestamps are already in seconds when return_seconds=True
        segments = []
        for ts in timestamps:
            segments.append({
                "start": round(float(ts["start"]), 3),
                "end": round(float(ts["end"]), 3),
            })

        logger.info(f"Telugu pipeline Stage 1: {len(segments)} VAD segments")
        return waveform, segments

    except Exception as e:
        raise RuntimeError(f"Telugu pipeline Stage 1: Silero VAD failed: {e}") from e


def _stage2_indic_conformer(waveform_tensor, speech_segments: List[Dict], language: str = "te") -> List[Dict]:
    """
    Transcribe each VAD segment using AI4Bharat IndicConformer in CTC mode.
    Returns [{start, end, text}].
    """
    model_id = os.environ.get("INDIC_CONFORMER_MODEL", "ai4bharat/indic-conformer-600m-multilingual")

    try:
        from transformers import AutoProcessor, AutoModelForCTC  # type: ignore
        import torch

        logger.info(f"Telugu pipeline Stage 2: loading IndicConformer from {model_id}")
        processor = AutoProcessor.from_pretrained(model_id)
        model = AutoModelForCTC.from_pretrained(model_id)
        model.eval()

    except Exception as e:
        raise RuntimeError(f"Telugu pipeline Stage 2: failed to load IndicConformer ({model_id}): {e}") from e

    import torch
    import numpy as np

    # Convert tensor to numpy for slicing
    waveform_np = waveform_tensor.numpy() if hasattr(waveform_tensor, "numpy") else np.array(waveform_tensor)

    transcript = []
    for seg in speech_segments:
        start_s = seg["start"]
        end_s = seg["end"]
        start_sample = int(start_s * SILERO_SAMPLE_RATE)
        end_sample = int(end_s * SILERO_SAMPLE_RATE)
        chunk = waveform_np[start_sample:end_sample]

        if len(chunk) < 100:
            continue

        try:
            inputs = processor(
                chunk,
                sampling_rate=SILERO_SAMPLE_RATE,
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
            logger.warning(f"Telugu pipeline Stage 2: segment [{start_s}-{end_s}] failed: {e}")

    return transcript


def _load_as_16k_mono_tensor(audio_path: str):
    """
    Load an audio file as a mono float32 tensor at 16 kHz.
    Returns (tensor, 16000).
    """
    import torch
    import numpy as np
    from pathlib import Path

    ext = Path(audio_path).suffix.lower()
    waveform_np = None
    orig_sr = None

    if ext == ".wav":
        import wave
        with wave.open(audio_path, "rb") as wf:
            n_channels = wf.getnchannels()
            orig_sr = wf.getframerate()
            n_frames = wf.getnframes()
            sample_width = wf.getsampwidth()
            raw = wf.readframes(n_frames)

        dtype_map = {1: np.int8, 2: np.int16, 4: np.int32}
        dtype = dtype_map.get(sample_width, np.int16)
        waveform_np = np.frombuffer(raw, dtype=dtype).astype(np.float32)
        max_val = float(2 ** (8 * sample_width - 1))
        waveform_np /= max_val
        if n_channels > 1:
            waveform_np = waveform_np.reshape(-1, n_channels).mean(axis=1)
    else:
        try:
            import soundfile as sf
            waveform_np, orig_sr = sf.read(audio_path, always_2d=False)
            if waveform_np.ndim > 1:
                waveform_np = waveform_np.mean(axis=1)
            waveform_np = waveform_np.astype(np.float32)
        except Exception:
            try:
                import librosa
                waveform_np, orig_sr = librosa.load(audio_path, sr=None, mono=True)
                waveform_np = waveform_np.astype(np.float32)
            except Exception as e:
                raise RuntimeError(f"Cannot load audio {audio_path}: {e}") from e

    # Resample to 16 kHz
    if orig_sr != SILERO_SAMPLE_RATE:
        try:
            import librosa
            waveform_np = librosa.resample(waveform_np, orig_sr=orig_sr, target_sr=SILERO_SAMPLE_RATE)
        except Exception:
            try:
                from scipy.signal import resample_poly
                from math import gcd
                g = gcd(orig_sr, SILERO_SAMPLE_RATE)
                waveform_np = resample_poly(waveform_np, SILERO_SAMPLE_RATE // g, orig_sr // g).astype(np.float32)
            except Exception as e:
                logger.warning(f"Resampling failed: {e}. Silero VAD may be inaccurate.")

    return torch.tensor(waveform_np, dtype=torch.float32), SILERO_SAMPLE_RATE
