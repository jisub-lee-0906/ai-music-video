from __future__ import annotations

CLIP_DIR = "clips"
MUSIC_DIR = "music"
STILL_DIR = "stills"


def audio_prefix(run_id: str) -> str:
    return f"{MUSIC_DIR}/audio_{str(run_id).strip()}"


def qwen_still_prefix(shot_id: str) -> str:
    return f"{STILL_DIR}/{str(shot_id).strip()}"


def ltx_clip_prefix(shot_id: str, mode: str) -> str:
    clean_mode = str(mode).strip() or "i2v"
    return f"{CLIP_DIR}/{str(shot_id).strip()}_{clean_mode}"
