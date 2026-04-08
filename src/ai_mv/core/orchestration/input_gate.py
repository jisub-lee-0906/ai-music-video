from __future__ import annotations

from typing import TypedDict

from ai_mv.core.contracts.errors import StageFailure


REQUIRED_INPUTS: dict[str, tuple[str, ...]] = {
    "plan": ("audio_plan", "audio_map"),
    "stills": ("shot_plan", "render_plan", "citypop_bible"),
    "clips": ("shot_plan", "render_plan", "still_results", "music_file"),
    "assemble": ("clip_results", "music_file"),
    "review": ("review_inputs",),
}


class ClipOutput(TypedDict):
    shot_id: str
    video: str


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
    if stage == "assemble":
        _validate_assemble_inputs(payload)
    if stage == "review":
        _validate_review_inputs(payload)


def _validate_assemble_inputs(payload: dict) -> None:
    clips = _require_list(payload.get("clip_results"), "assemble clip_results")
    for idx, row in enumerate(clips, start=1):
        item: ClipOutput = _require_dict(row, f"assemble clip_results[{idx}]")
        _require_non_empty_str(item.get("shot_id"), f"assemble clip_results[{idx}].shot_id")
        _require_non_empty_str(item.get("video"), f"assemble clip_results[{idx}].video")
    _require_non_empty_str(payload.get("music_file"), "assemble music_file")


def _validate_review_inputs(payload: dict) -> None:
    review_inputs = _require_dict(payload.get("review_inputs"), "review review_inputs")
    _require_non_empty_str(review_inputs.get("music_file"), "review review_inputs.music_file")


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
