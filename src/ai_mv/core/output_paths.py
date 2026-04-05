from __future__ import annotations

ANCHOR_DIR = "anchors"
KEYFRAME_DIR = "keyframes"
CLIP_DIR = "clips"
MUSIC_DIR = "music"


def audio_prefix(run_id: str) -> str:
    return f"{MUSIC_DIR}/audio_{str(run_id).strip()}"


def master_anchor_prefix() -> str:
    return f"{ANCHOR_DIR}/character_master"


def _seq_tag(index: int | None) -> str:
    try:
        value = int(index or 0)
    except Exception:
        value = 0
    return f"{value:03d}_" if value > 0 else ""


def flux2_ref_frame_prefix(shot_id: str, frame_name: str = "", sequence_index: int | None = None) -> str:
    return f"{KEYFRAME_DIR}/ref_{_seq_tag(sequence_index)}{str(shot_id).strip()}"


def wan_clip_prefix(
    start_shot_id: str,
    end_shot_id: str,
    start_index: int | None = None,
    end_index: int | None = None,
) -> str:
    return (
        f"{CLIP_DIR}/wan_"
        f"{_seq_tag(start_index)}{str(start_shot_id).strip()}__"
        f"{_seq_tag(end_index)}{str(end_shot_id).strip()}"
    )
