from __future__ import annotations

import traceback

from ai_mv.core.artifacts.publish import write_pipeline_artifacts
from ai_mv.core.contracts.stage_io import StageInput
from ai_mv.core.orchestration.input_gate import validate_stage_input
from ai_mv.core.orchestration.preflight_steps import add_audio
from ai_mv.core.orchestration.preflight_steps import add_flux2_ref
from ai_mv.core.orchestration.preflight_steps import add_lyrics_timeline
from ai_mv.core.orchestration.preflight_steps import add_shot_router
from ai_mv.core.orchestration.preflight_steps import add_shot_timeline
from ai_mv.core.orchestration.preflight_steps import add_story_bible
from ai_mv.core.orchestration.preflight_steps import add_wan
from ai_mv.core.orchestration.stage_runs import run_preview_stage
from ai_mv.core.state.state_snapshot import save_snapshot
from ai_mv.core.state.state_store import init_run_state


def run_preflight(config: dict, run_id: str = "", allow_existing_run: bool = False) -> str:
    cfg = dict(config)
    state = init_run_state(cfg, run_id, allow_existing=allow_existing_run, scope="preflight")
    payload = {"selected_profile": str(cfg.get("profile", "")).strip()}
    save_snapshot(state, payload)
    stage_input = StageInput(run_id=state["run_id"], config=cfg, payload=payload)
    try:
        _run_preflight_stage(state, stage_input, "acestep_music", add_audio)
        _run_preflight_stage(state, stage_input, "lyrics_timeline", add_lyrics_timeline)
        _run_preflight_stage(state, stage_input, "visual_story_bible", add_story_bible)
        _run_preflight_stage(state, stage_input, "shot_timeline", add_shot_timeline)
        _run_preflight_stage(state, stage_input, "shot_router", add_shot_router)
        _run_preflight_stage(state, stage_input, "flux2_ref_chain", add_flux2_ref)
        _run_preflight_stage(state, stage_input, "wan_interpolation", add_wan)
        state["current_stage"] = "preflight"
        state["status"] = "done"
    except Exception as exc:
        state["status"] = "failed"
        state["failure_reason"] = f"{state['current_stage']}: {exc}" if state["current_stage"] else str(exc)
        state["failure_traceback"] = traceback.format_exc()
        save_snapshot(state, stage_input.payload)
        _write_preflight_artifacts(state, stage_input.payload, cfg)
        raise
    save_snapshot(state, stage_input.payload)
    _write_preflight_artifacts(state, stage_input.payload, cfg)
    return state["run_id"]


def _run_preflight_stage(state: dict, stage_input: StageInput, name: str, fn) -> None:
    run_preview_stage(
        state,
        stage_input,
        name,
        fn,
        save_snapshot=save_snapshot,
        validate_stage_input=validate_stage_input,
    )


def _write_preflight_artifacts(state: dict, payload: dict, config: dict) -> None:
    write_pipeline_artifacts(state, payload, config)
