from __future__ import annotations

ANCHOR_DIR = "anchors"
KEYFRAME_DIR = "keyframes"
CLIP_DIR = "clips"
MUSIC_DIR = "music"


def audio_prefix(run_id: str) -> str:
    return f"{MUSIC_DIR}/{str(run_id).strip()}_music"


def master_anchor_prefix() -> str:
    return f"{ANCHOR_DIR}/character_master"


def flux2_ref_frame_prefix(shot_id: str, frame_name: str) -> str:
    return f"{KEYFRAME_DIR}/ref_{str(shot_id).strip()}_{str(frame_name).strip()}"


def wan_clip_prefix(start_shot_id: str, end_shot_id: str) -> str:
    return f"{CLIP_DIR}/wan_{str(start_shot_id).strip()}__{str(end_shot_id).strip()}"
