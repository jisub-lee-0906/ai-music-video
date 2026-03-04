from __future__ import annotations

from ai_mv.engines.acestep_1_5_split.mapper import map_audio_workflow
from ai_mv.infra.comfy_client import run_workflow


def run_audio_split(config: dict, plan: dict) -> dict:
    wf = map_audio_workflow(config, plan)
    result = run_workflow(config, "audio_ace_step_1_5_split.api.json", wf)
    duration = 120.0
    return {
        "duration_sec": duration,
        "bpm_estimate": 120,
        "sections": _sections(duration),
        "music_file": _pick_audio_file(result.get("files", []), config),
    }


def _sections(duration: float) -> list[dict]:
    return [
        {"name": "intro", "start_sec": 0.0, "end_sec": duration * 0.15},
        {"name": "verse", "start_sec": duration * 0.15, "end_sec": duration * 0.40},
        {"name": "chorus", "start_sec": duration * 0.40, "end_sec": duration * 0.60},
        {"name": "bridge", "start_sec": duration * 0.60, "end_sec": duration * 0.78},
        {"name": "outro", "start_sec": duration * 0.78, "end_sec": duration},
    ]


def _pick_audio_file(files: list[str], config: dict) -> str:
    for name in files:
        low = str(name).lower()
        if low.endswith((".wav", ".mp3", ".flac", ".m4a")):
            return name
    return str(config.get("audio", {}).get("source_wav", "master.wav"))
