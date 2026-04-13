from __future__ import annotations

from ai_mv.core.artifacts.publish import write_pipeline_artifacts
from ai_mv.core.contracts.stage_io import StageInput
from ai_mv.core.orchestration.input_gate import validate_stage_input
from ai_mv.core.orchestration.stage_runs import run_result_stage
from ai_mv.core.state.state_snapshot import save_snapshot
from ai_mv.core.state.state_store import init_run_state
from ai_mv.core.stages.acestep_music import run_acestep_music
from ai_mv.core.stages.assemble_mv import run_assemble_mv
from ai_mv.core.stages.plan_citypop_mv import run_plan_citypop_mv
from ai_mv.core.stages.render_clips import run_render_clips
from ai_mv.core.stages.render_stills import run_render_stills
from ai_mv.core.stages.review_outputs import run_review_outputs


def run_pipeline(config: dict, run_id: str = "", allow_existing_run: bool = False) -> str:
    cfg = dict(config)
    state = init_run_state(cfg, run_id, allow_existing=allow_existing_run)
    stage_input = StageInput(
        run_id=state["run_id"],
        config=cfg,
        payload={
            "concept_text": str(cfg.get("concept_text", "")).strip(),
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
        ("plan", run_plan_citypop_mv),
        ("stills", run_render_stills),
        ("clips", run_render_clips),
        ("assemble", run_assemble_mv),
        ("review", run_review_outputs),
    ]
