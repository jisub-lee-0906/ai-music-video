from __future__ import annotations

from ai_mv.engines.acestep_1_5_split.mapper import audio_required_inputs, map_audio_workflow
from ai_mv.infra.comfy_client import run_workflow
from ai_mv.utils.time_utils import ffprobe_duration


def run_audio_split(config: dict, plan: dict) -> dict:
    wf = map_audio_workflow(config, plan)
    result = run_workflow(config, "audio_ace_step_1_5_tta.api.json", wf, audio_required_inputs())
    music_file = _pick_audio_file(result["files"])
    duration = ffprobe_duration(music_file)
    if duration <= 0:
        raise RuntimeError(f"invalid audio duration: {music_file}")
    return {
        "duration_sec": duration,
        "bpm_estimate": int(plan["bpm"]),
        "sections": _sections(duration),
        "music_file": music_file,
    }


def _sections(duration: float) -> list[dict]:
    return [
        {"name": "intro", "start_sec": 0.0, "end_sec": duration * 0.15},
        {"name": "verse", "start_sec": duration * 0.15, "end_sec": duration * 0.40},
        {"name": "chorus", "start_sec": duration * 0.40, "end_sec": duration * 0.60},
        {"name": "bridge", "start_sec": duration * 0.60, "end_sec": duration * 0.78},
        {"name": "outro", "start_sec": duration * 0.78, "end_sec": duration},
    ]


def _pick_audio_file(files: list[str]) -> str:
    for name in files:
        low = str(name).lower()
        if low.endswith((".wav", ".mp3", ".flac", ".m4a")):
            return name
    raise RuntimeError("audio output file not found")
