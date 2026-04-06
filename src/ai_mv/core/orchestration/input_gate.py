from __future__ import annotations

from typing import TypedDict

from ai_mv.core.contracts.errors import StageFailure


REQUIRED_INPUTS: dict[str, tuple[str, ...]] = {
    "lyrics_timeline": ("audio_plan", "audio_map"),
    "scene_outline": ("audio_plan", "audio_map", "lyrics_timeline"),
    "shot_density_refiner": ("scene_outline",),
    "direction_plan": ("wan_safe_scene_outline",),
    "prompt_plan": ("direction_plan",),
    "backend_preview": ("prompt_plan",),
    "tti_anchor": ("prompt_plan",),
    "flux2_ref_chain": ("prompt_plan", "master_anchor"),
    "wan_interpolation": ("prompt_plan", "flux2_ref_images", "clip_routes"),
    "merge_mux": ("clips", "music_file"),
}


class ClipOutput(TypedDict):
    shot_id: str
    video: str


class ClipRoute(TypedDict, total=False):
    shot_id: str
    anchor: str
    duration_sec: float
    use_ref: bool


def validate_stage_input(stage: str, payload: dict) -> None:
    required = REQUIRED_INPUTS.get(stage, ())
    missing = [key for key in required if key not in payload]
    if missing:
        names = ", ".join(missing)
        raise StageFailure(f"{stage} missing required inputs: {names}")
    empty = [key for key in required if _is_empty(payload.get(key))]
    if empty:
        names = ", ".join(empty)
        raise StageFailure(f"{stage} empty required inputs: {names}")
    _validate_stage_shape(stage, payload)


def _validate_stage_shape(stage: str, payload: dict) -> None:
    if stage == "merge_mux":
        _validate_merge_inputs(payload)


def _validate_merge_inputs(payload: dict) -> None:
    clips = _require_list(payload.get("clips"), "merge_mux clips")
    for idx, row in enumerate(clips, start=1):
        item: ClipOutput = _require_dict(row, f"merge_mux clips[{idx}]")
        _require_non_empty_str(item.get("shot_id"), f"merge_mux clips[{idx}].shot_id")
        _require_non_empty_str(item.get("video"), f"merge_mux clips[{idx}].video")
    _require_non_empty_str(payload.get("music_file"), "merge_mux music_file")


def _require_list(value: object, label: str) -> list:
    if not isinstance(value, list) or not value:
        raise StageFailure(f"{label} must be a non-empty list")
    return value


def _require_dict(value: object, label: str) -> dict:
    if not isinstance(value, dict):
        raise StageFailure(f"{label} must be an object")
    return value


def _require_non_empty_str(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise StageFailure(f"{label} must be a non-empty string")
    return value.strip()


def _require_positive_number(value: object, label: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or float(value) <= 0:
        raise StageFailure(f"{label} must be a positive number")
    return float(value)


def _is_empty(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, dict, tuple, set)):
        return len(value) == 0
    return False
