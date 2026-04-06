from __future__ import annotations

from ai_mv.core.artifacts.publish import write_pipeline_artifacts
from ai_mv.core.contracts.stage_io import StageInput
from ai_mv.core.director_brief import build_director_brief_intent
from ai_mv.core.orchestration.input_gate import validate_stage_input
from ai_mv.core.orchestration.stage_runs import run_result_stage
from ai_mv.core.state.state_snapshot import save_snapshot
from ai_mv.core.state.state_store import init_run_state
from ai_mv.core.stages.acestep_music import run_acestep_music
from ai_mv.core.stages.keyframes import run_keyframes
from ai_mv.core.stages.merge_mux import run_merge_mux
from ai_mv.core.stages.storyboard import run_storyboard
from ai_mv.core.stages.wan_interpolation import run_wan_interpolation


def run_pipeline(config: dict, run_id: str = "", allow_existing_run: bool = False) -> str:
    cfg = dict(config)
    state = init_run_state(cfg, run_id, allow_existing=allow_existing_run)
    stage_input = StageInput(
        run_id=state["run_id"],
        config=cfg,
        payload={
            "selected_brief": str(cfg.get("brief", "")).strip(),
            "story_profile": build_director_brief_intent(cfg),
            "workflow_inputs": {},
        },
    )
    save_snapshot(state, stage_input.payload)
    for name, stage_fn in _ordered_stages():
        ok = run_result_stage(
            state,
            stage_input,
            name,
            stage_fn,
            save_snapshot=save_snapshot,
            validate_stage_input=validate_stage_input,
        )
        if not ok:
            break
    state["status"] = "done" if state["status"] != "failed" else "failed"
    save_snapshot(state, stage_input.payload)
    write_pipeline_artifacts(state, stage_input.payload, cfg)
    return state["run_id"]


def _ordered_stages() -> list[tuple[str, callable]]:
    return [
        ("audio", run_acestep_music),
        ("storyboard", run_storyboard),
        ("keyframes", run_keyframes),
        ("clips", run_wan_interpolation),
        ("merge", run_merge_mux),
    ]
