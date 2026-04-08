from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path


def analyze_audio_timing(
    path: str | Path,
    *,
    bpm_hint: int = 0,
    beats_per_bar: int = 4,
) -> dict:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg not found for audio beat analysis")
    try:
        import librosa  # type: ignore
        import numpy as np  # type: ignore
    except Exception as exc:  # pragma: no cover - env/dependency guard
        raise RuntimeError("audio beat analysis dependencies missing: librosa, numpy") from exc
    source = Path(path)
    if not source.exists():
        raise RuntimeError(f"audio file not found for beat analysis: {source}")
    with tempfile.TemporaryDirectory(prefix="ai_mv_audio_timing_") as tmpdir:
        wav_path = Path(tmpdir) / "analysis.wav"
        cmd = [
            ffmpeg,
            "-y",
            "-i",
            str(source),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "22050",
            str(wav_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0 or not wav_path.exists():
            detail = (result.stderr or "").strip() or (result.stdout or "").strip() or "ffmpeg decode failed"
            raise RuntimeError(f"audio beat analysis decode failed: {detail}")
        y, sr = librosa.load(str(wav_path), sr=22050, mono=True)
    if getattr(y, "size", 0) <= 0:
        raise RuntimeError("audio beat analysis failed: empty decoded waveform")
    onset_env = librosa.onset.onset_strength(y=y, sr=sr, aggregate=np.median)
    tempo, beat_frames = librosa.beat.beat_track(
        onset_envelope=onset_env,
        sr=sr,
        start_bpm=float(bpm_hint or 120),
        trim=False,
    )
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)
    cleaned = _clean_times(beat_times.tolist())
    if len(cleaned) < max(4, beats_per_bar * 2):
        raise RuntimeError(f"audio beat analysis produced too few beats: {len(cleaned)}")
    detected_bpm = int(round(float(tempo))) if float(tempo) > 0 else int(bpm_hint or 0)
    return {
        "detected_bpm": detected_bpm if detected_bpm > 0 else 120,
        "beat_times_sec": cleaned,
        "beats_per_bar": max(1, int(beats_per_bar)),
    }


def _clean_times(values: list[float]) -> list[float]:
    out: list[float] = []
    prev = -1.0
    for raw in values:
        try:
            value = round(float(raw), 6)
        except Exception:
            continue
        if value < 0:
            continue
        if prev >= 0 and abs(value - prev) < 0.05:
            continue
        out.append(value)
        prev = value
    return out
