from __future__ import annotations

import traceback
from collections.abc import Callable

from ai_mv.core.contracts.errors import StageFailure
from ai_mv.core.contracts.stage_io import StageInput
from ai_mv.core.contracts.stage_io import StageOutput

PROTECTED_PAYLOAD_KEYS = {
    "selected_brief",
    "director_brief_intent",
    "audio_plan",
    "audio_map",
    "music_file",
    "lyrics_timeline",
    "scene_plan",
    "director_plan",
    "render_plan",
    "backend_preview",
    "director_cards_preview",
    "anchors",
    "clip_routes",
    "flux2_ref_images",
    "clips",
    "merge_plan",
    "final_video",
}


def merge_stage_payload(target: dict, patch: dict, stage: str) -> None:
    if not isinstance(patch, dict):
        raise StageFailure(f"{stage} returned invalid payload: expected object")
    collisions = [
        key
        for key, value in patch.items()
        if key in PROTECTED_PAYLOAD_KEYS and key in target and target[key] != value
    ]
    if collisions:
        names = ", ".join(sorted(collisions))
        raise StageFailure(f"{stage} attempted to overwrite protected payload keys: {names}")
    target.update(patch)


def run_result_stage(
    state: dict,
    stage_input: StageInput,
    name: str,
    stage_fn: Callable[[StageInput], StageOutput],
    *,
    save_snapshot: Callable[[dict, dict], None],
    validate_stage_input: Callable[[str, dict], None],
) -> bool:
    state["current_stage"] = name
    save_snapshot(state, stage_input.payload)
    try:
        validate_stage_input(name, stage_input.payload)
        result = stage_fn(stage_input)
        merge_stage_payload(stage_input.payload, result.payload, name)
        state["completed_stages"].append(name)
        if result.status != "done":
            state["status"] = "failed"
            state["failure_reason"] = result.error or f"stage={name}"
            return False
    except Exception as exc:
        state["status"] = "failed"
        state["failure_reason"] = f"{name}: {exc}"
        state["failure_traceback"] = traceback.format_exc()
        return False
    save_snapshot(state, stage_input.payload)
    return True


def run_preview_stage(
    state: dict,
    stage_input: StageInput,
    name: str,
    fn: Callable[[StageInput], None],
    *,
    save_snapshot: Callable[[dict, dict], None],
    validate_stage_input: Callable[[str, dict], None],
) -> None:
    state["current_stage"] = name
    save_snapshot(state, stage_input.payload)
    validate_stage_input(name, stage_input.payload)
    fn(stage_input)
    state["completed_stages"].append(name)
    save_snapshot(state, stage_input.payload)
