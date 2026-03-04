from __future__ import annotations

from pathlib import Path

from ai_mv.engines.acestep_1_5_split.policy import audio_policy


def build_audio_plan(config: dict, payload: dict) -> dict:
    audio = config.get("audio", {})
    plan = {
        "source_wav": audio.get("source_wav", ""),
        "sample_rate": audio.get("sample_rate", 48000),
        "lyrics": _load_lyrics(audio.get("lyrics_file", "")),
        "tags": ", ".join(audio.get("keywords", [])),
        "filename_prefix": f"artifacts/runs_state/{payload.get('run_id', 'run')}/audio/music",
    }
    plan.update(audio_policy(config))
    return plan


def _load_lyrics(path: str) -> str:
    if not path:
        return ""
    p = Path(path)
    if not p.exists():
        return ""
    return p.read_text(encoding="utf-8").strip()

