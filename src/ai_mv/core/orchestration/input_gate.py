from __future__ import annotations

from ai_mv.core.contracts.errors import StageFailure


REQUIRED_INPUTS: dict[str, tuple[str, ...]] = {
    "tti_anchor": ("audio_map",),
    "uso_chain": ("anchors",),
    "wan_interpolation": ("uso_images",),
    "merge_mux": ("clips", "music_file"),
}


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


def _is_empty(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, dict, tuple, set)):
        return len(value) == 0
    return False
