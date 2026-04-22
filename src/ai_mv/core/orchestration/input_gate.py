from __future__ import annotations

from typing import TypedDict

from ai_mv.core.contracts.errors import StageFailure


REQUIRED_INPUTS: dict[str, tuple[str, ...]] = {
    "plan": ("audio_plan", "audio_map"),
    "stills": ("shot_plan", "material_plan", "render_plan", "style_bible"),
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
    if stage == "stills":
        _validate_stills_inputs(payload)
    if stage == "clips":
        _validate_clips_inputs(payload)
    if stage == "assemble":
        _validate_assemble_inputs(payload)
    if stage == "review":
        _validate_review_inputs(payload)


def _validate_stills_inputs(payload: dict) -> None:
    shots = _require_list(payload.get("shot_plan"), "stills shot_plan")
    materials = _require_list(payload.get("material_plan"), "stills material_plan")
    renders = _require_list(payload.get("render_plan"), "stills render_plan")
    _require_unique_non_empty_ids(materials, "material_id", "stills material_plan")
    _require_unique_non_empty_ids(shots, "shot_id", "stills shot_plan")
    _require_unique_non_empty_ids(renders, "shot_id", "stills render_plan")
    material_ids = {
        _require_non_empty_str(row.get("material_id"), f"stills material_plan[{idx}].material_id")
        for idx, row in enumerate(materials, start=1)
        for row in [_require_dict(row, f"stills material_plan[{idx}]")]
    }
    render_material_ids = {}
    render_shot_ids = set()
    for idx, row in enumerate(renders, start=1):
        item = _require_dict(row, f"stills render_plan[{idx}]")
        shot_id = _require_non_empty_str(item.get("shot_id"), f"stills render_plan[{idx}].shot_id")
        render_material_id = _require_non_empty_str(item.get("material_id"), f"stills render_plan[{idx}].material_id")
        if render_material_id not in material_ids:
            raise StageFailure(f"stills render_plan[{idx}].material_id must reference an existing material_plan row")
        render_material_ids[shot_id] = render_material_id
        render_shot_ids.add(shot_id)
    shot_ids = set()
    used_material_ids = set()
    for idx, row in enumerate(shots, start=1):
        item = _require_dict(row, f"stills shot_plan[{idx}]")
        shot_id = _require_non_empty_str(item.get("shot_id"), f"stills shot_plan[{idx}].shot_id")
        shot_ids.add(shot_id)
        shot_material_id = _require_non_empty_str(item.get("material_id"), f"stills shot_plan[{idx}].material_id")
        if shot_material_id not in material_ids:
            raise StageFailure(f"stills shot_plan[{idx}].material_id must reference an existing material_plan row")
        render_material_id = render_material_ids.get(shot_id)
        if render_material_id is None:
            raise StageFailure(f"stills shot_plan[{idx}].shot_id must be present in render_plan")
        if shot_material_id != render_material_id:
            raise StageFailure(f"stills shot_plan[{idx}].material_id must match render_plan material linkage")
        used_material_ids.add(shot_material_id)
    extra_render_ids = sorted(render_shot_ids - shot_ids)
    if extra_render_ids:
        raise StageFailure("stills render_plan contains shot_ids not present in shot_plan")
    unused_material_ids = sorted(material_ids - used_material_ids)
    if unused_material_ids:
        raise StageFailure("stills material_plan contains unreferenced material_id rows")


def _validate_clips_inputs(payload: dict) -> None:
    shots = _require_list(payload.get("shot_plan"), "clips shot_plan")
    renders = _require_list(payload.get("render_plan"), "clips render_plan")
    stills = _require_list(payload.get("still_results"), "clips still_results")
    _require_unique_non_empty_ids(shots, "shot_id", "clips shot_plan")
    _require_unique_non_empty_ids(renders, "shot_id", "clips render_plan")
    _require_unique_non_empty_ids(stills, "shot_id", "clips still_results")
    shot_material_ids = {}
    shot_ids = set()
    for idx, row in enumerate(shots, start=1):
        item = _require_dict(row, f"clips shot_plan[{idx}]")
        shot_id = _require_non_empty_str(item.get("shot_id"), f"clips shot_plan[{idx}].shot_id")
        shot_ids.add(shot_id)
        shot_material_ids[shot_id] = _require_non_empty_str(item.get("material_id"), f"clips shot_plan[{idx}].material_id")
    render_material_ids = {}
    render_shot_ids = set()
    for idx, row in enumerate(renders, start=1):
        item = _require_dict(row, f"clips render_plan[{idx}]")
        shot_id = _require_non_empty_str(item.get("shot_id"), f"clips render_plan[{idx}].shot_id")
        render_shot_ids.add(shot_id)
        material_id = str(item.get("material_id", "")).strip()
        if material_id:
            render_material_ids[shot_id] = material_id
        expected_shot_material_id = shot_material_ids.get(shot_id)
        if material_id and expected_shot_material_id and material_id != expected_shot_material_id:
            raise StageFailure(f"clips render_plan[{idx}].material_id must match shot_plan material linkage")
    shot_ids = set(shot_material_ids.keys())
    still_shot_ids = set()
    for idx, row in enumerate(stills, start=1):
        item = _require_dict(row, f"clips still_results[{idx}]")
        shot_id = _require_non_empty_str(item.get("shot_id"), f"clips still_results[{idx}].shot_id")
        still_shot_ids.add(shot_id)
        _require_non_empty_str(item.get("image"), f"clips still_results[{idx}].image")
        expected_material_id = render_material_ids.get(shot_id) or shot_material_ids.get(shot_id)
        material_id = str(item.get("material_id", "")).strip()
        if expected_material_id:
            if material_id != expected_material_id:
                raise StageFailure(f"clips still_results[{idx}].material_id must match shot/render material linkage")
        else:
            _require_non_empty_str(item.get("material_id"), f"clips still_results[{idx}].material_id")
    extra_still_ids = sorted(still_shot_ids - shot_ids)
    if extra_still_ids:
        raise StageFailure("clips still_results contains shot_ids not present in shot_plan")
    extra_render_ids = sorted(render_shot_ids - shot_ids)
    if extra_render_ids:
        raise StageFailure("clips render_plan contains shot_ids not present in shot_plan")


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


def _require_unique_non_empty_ids(rows: list, key: str, label: str) -> None:
    seen: set[str] = set()
    for idx, row in enumerate(rows, start=1):
        item = _require_dict(row, f"{label}[{idx}]")
        value = _require_non_empty_str(item.get(key), f"{label}[{idx}].{key}")
        if value in seen:
            raise StageFailure(f"{label} contains duplicate {key}: {value}")
        seen.add(value)


def _is_empty(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, dict, tuple, set)):
        return len(value) == 0
    return False
