from __future__ import annotations

import traceback

from ai_mv.core.artifacts.publish import write_pipeline_artifacts
from ai_mv.core.contracts.errors import StageFailure
from ai_mv.core.contracts.stage_io import StageInput
from ai_mv.core.orchestration.input_gate import validate_stage_input
from ai_mv.core.orchestration.scheduler import schedule
from ai_mv.core.state.state_snapshot import save_snapshot
from ai_mv.core.state.state_store import init_run_state

PROTECTED_PAYLOAD_KEYS = {
    "selected_profile",
    "profile_intent",
    "audio_plan",
    "audio_map",
    "music_file",
    "lyrics_timeline",
    "visual_story_bible",
    "anchors",
    "shot_timeline",
    "clip_routes",
    "flux2_ref_images",
    "clips",
    "merge_plan",
    "final_video",
}


def run_pipeline(config: dict, run_id: str = "", allow_existing_run: bool = False) -> str:
    cfg = dict(config)
    state = init_run_state(cfg, run_id, allow_existing=allow_existing_run)
    stage_input = StageInput(
        run_id=state["run_id"],
        config=cfg,
        payload={"selected_profile": str(cfg.get("profile", "")).strip()},
    )
    save_snapshot(state, stage_input.payload)

    for name, stage_fn in schedule():
        state["current_stage"] = name
        save_snapshot(state, stage_input.payload)
        try:
            validate_stage_input(name, stage_input.payload)
            result = stage_fn(stage_input)
            _merge_stage_payload(stage_input.payload, result.payload, name)
            state["completed_stages"].append(name)
            if result.status != "done":
                state["status"] = "failed"
                state["failure_reason"] = result.error or f"stage={name}"
                break
        except Exception as exc:
            state["status"] = "failed"
            state["failure_reason"] = f"{name}: {exc}"
            state["failure_traceback"] = traceback.format_exc()
            break
        save_snapshot(state, stage_input.payload)

    state["status"] = "done" if state["status"] != "failed" else "failed"
    save_snapshot(state, stage_input.payload)
    write_pipeline_artifacts(state, stage_input.payload, cfg)
    return state["run_id"]


def _merge_stage_payload(target: dict, patch: dict, stage: str) -> None:
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
