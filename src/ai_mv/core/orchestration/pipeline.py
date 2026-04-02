from __future__ import annotations

from ai_mv.core.artifacts.publish import write_pipeline_artifacts
from ai_mv.core.contracts.stage_io import StageInput
from ai_mv.core.director_brief import build_director_brief_intent
from ai_mv.core.orchestration.input_gate import validate_stage_input
from ai_mv.core.orchestration.stage_runs import run_result_stage
from ai_mv.core.state.state_snapshot import save_snapshot
from ai_mv.core.state.state_store import init_run_state
from ai_mv.core.stages.acestep_music import run_acestep_music
from ai_mv.core.stages.backend_preview import run_backend_preview
from ai_mv.core.stages.director_plan import run_director_plan
from ai_mv.core.stages.flux2_ref_chain import run_flux2_ref_chain
from ai_mv.core.stages.lyrics_timeline import run_lyrics_timeline
from ai_mv.core.stages.merge_mux import run_merge_mux
from ai_mv.core.stages.render_plan import run_render_plan
from ai_mv.core.stages.scene_plan import run_scene_plan
from ai_mv.core.stages.tti_anchor import run_tti_anchor
from ai_mv.core.stages.wan_interpolation import run_wan_interpolation


def run_pipeline(config: dict, run_id: str = "", allow_existing_run: bool = False) -> str:
    cfg = dict(config)
    state = init_run_state(cfg, run_id, allow_existing=allow_existing_run)
    stage_input = StageInput(
        run_id=state["run_id"],
        config=cfg,
        payload={
            "selected_brief": str(cfg.get("brief", "")).strip(),
            "director_brief_intent": build_director_brief_intent(cfg),
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
        ("acestep_music", run_acestep_music),
        ("lyrics_timeline", run_lyrics_timeline),
        ("scene_plan", run_scene_plan),
        ("director_plan", run_director_plan),
        ("render_plan", run_render_plan),
        ("backend_preview", run_backend_preview),
        ("tti_anchor", run_tti_anchor),
        ("flux2_ref_chain", run_flux2_ref_chain),
        ("wan_interpolation", run_wan_interpolation),
        ("merge_mux", run_merge_mux),
    ]
