from __future__ import annotations

from pathlib import Path
import re

from ai_mv.infra.comfy_local import comfy_output_dir

AI_MV_NAMESPACE = "ai_mv"
RUNS_DIR = "runs"
PREFLIGHT_DIR = "preflight"
AUDIO_DIR = "audio"
CLIP_DIR = "clips"
FINAL_DIR = "final"
STILL_DIR = "stills"
AUDIO_FILE_STEM = "song"
FINAL_FILE_NAME = "mv.mp4"


def audio_prefix(run_id: str, scope: str = "run") -> str:
    return f"{_media_root(run_id, scope)}/{AUDIO_DIR}/{AUDIO_FILE_STEM}"


def still_prefix(run_id: str, shot_id: str, scope: str = "run") -> str:
    return f"{_media_root(run_id, scope)}/{STILL_DIR}/shot-{_clean_segment(shot_id)}"


def ltx_clip_prefix(run_id: str, shot_id: str, mode: str, scope: str = "run") -> str:
    clean_mode = _clean_segment(mode) or "ia2v"
    return f"{_media_root(run_id, scope)}/{CLIP_DIR}/shot-{_clean_segment(shot_id)}-{clean_mode}"


def final_video_path(config: dict, run_id: str, scope: str = "run") -> Path:
    out = comfy_output_dir(config)
    target = out / _media_root(run_id, scope) / FINAL_DIR / FINAL_FILE_NAME
    target.parent.mkdir(parents=True, exist_ok=True)
    return target


def _media_root(run_id: str, scope: str = "run") -> str:
    scope_dir = PREFLIGHT_DIR if str(scope).strip().lower() == "preflight" else RUNS_DIR
    return f"{AI_MV_NAMESPACE}/{scope_dir}/{_clean_segment(run_id)}"


def _clean_segment(value: str) -> str:
    raw = str(value).strip().replace("\\", "/")
    pieces = []
    for part in raw.split("/"):
        part = part.strip()
        if not part or part == "." or part == "..":
            continue
        safe = re.sub(r"[^A-Za-z0-9._-]+", "-", part)
        safe = safe.strip(".-_")
        if safe:
            pieces.append(safe)
    return "-".join(pieces)
