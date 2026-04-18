from __future__ import annotations

from ai_mv.core.artifacts.publish import write_pipeline_artifacts
from ai_mv.core.contracts.stage_io import StageInput
from ai_mv.core.orchestration.input_gate import validate_stage_input
from ai_mv.core.orchestration.stage_runs import run_result_stage
from ai_mv.core.state.state_snapshot import save_snapshot
from ai_mv.core.state.state_store import init_run_state
from ai_mv.core.stages.acestep_music import run_acestep_music
from ai_mv.core.stages.assemble_mv import run_assemble_mv
from ai_mv.core.stages.plan_mv import run_plan_mv
from ai_mv.core.stages.render_clips import run_render_clips
from ai_mv.core.stages.render_stills import run_render_stills
from ai_mv.core.stages.rerender_loop import run_rerender_loop
from ai_mv.core.stages.review_stage import run_review_stage


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
        if name == "review" and _review_needs_rerender(stage_input.payload.get("review_report")):
            ok = run_result_stage(
                state,
                stage_input,
                "rerender",
                run_rerender_loop,
                save_snapshot=save_snapshot,
                validate_stage_input=validate_stage_input,
            )
            if not ok:
                break
            _ensure_rerender_outcome(stage_input.payload)
    state["status"] = "done" if state["status"] != "failed" else "failed"
    save_snapshot(state, stage_input.payload)
    write_pipeline_artifacts(state, stage_input.payload, cfg)
    return state["run_id"]


def _ordered_stages() -> list[tuple[str, callable]]:
    return [
        ("audio", run_acestep_music),
        ("plan", run_plan_mv),
        ("stills", run_render_stills),
        ("clips", run_render_clips),
        ("assemble", run_assemble_mv),
        ("review", run_review_stage),
    ]



def _review_needs_rerender(review_report: object) -> bool:
    if not isinstance(review_report, dict):
        return False
    status = str(review_report.get("status", "")).strip()
    rerender_targets = review_report.get("rerender_targets")
    rerender_payloads = review_report.get("rerender_execution_payloads")
    return status == "needs_rerender" or bool(rerender_targets) or bool(rerender_payloads)



def _ensure_rerender_outcome(payload: dict) -> None:
    if not isinstance(payload, dict) or isinstance(payload.get("rerender_outcome"), dict):
        return
    review_report = payload.get("review_report")
    if not isinstance(review_report, dict):
        payload["rerender_outcome"] = {"attempted": True, "resolved": False, "exhausted": True}
        return
    unresolved = _review_needs_rerender(review_report)
    payload["rerender_outcome"] = {
        "attempted": True,
        "resolved": not unresolved,
        "exhausted": unresolved,
    }
