from __future__ import annotations

ANCHOR_DIR = "anchors"
KEYFRAME_DIR = "keyframes"
CLIP_DIR = "clips"
MUSIC_DIR = "music"


def audio_prefix(run_id: str) -> str:
    return f"{MUSIC_DIR}/{str(run_id).strip()}_music"


def tti_anchor_prefix() -> str:
    return f"{ANCHOR_DIR}/character_master"


def uso_frame_prefix(shot_id: str, frame_name: str) -> str:
    return f"{KEYFRAME_DIR}/{str(shot_id).strip()}_{str(frame_name).strip()}"


def wan_clip_prefix(shot_id: str) -> str:
    return f"{CLIP_DIR}/{str(shot_id).strip()}"
