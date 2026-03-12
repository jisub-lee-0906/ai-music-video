from __future__ import annotations

import traceback

from ai_mv.core.artifacts.manifest import write_manifest
from ai_mv.core.artifacts.prompt_preview import write_prompt_preview
from ai_mv.core.artifacts.quality_review import write_quality_review
from ai_mv.core.artifacts.run_summary import write_run_summary
from ai_mv.core.artifacts.summary import write_summary
from ai_mv.core.artifacts.workflow_inputs_preview import write_workflow_inputs_preview
from ai_mv.core.quality_review import build_quality_review, build_run_summary
from ai_mv.core.contracts.stage_io import StageInput
from ai_mv.core.orchestration.input_gate import validate_stage_input
from ai_mv.core.orchestration.scheduler import schedule
from ai_mv.core.state.state_snapshot import save_snapshot
from ai_mv.core.state.state_store import init_run_state


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
            stage_input.payload.update(result.payload)
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
    write_manifest(state, stage_input.payload)
    write_summary(state, stage_input.payload)
    write_prompt_preview(state, stage_input.payload)
    write_workflow_inputs_preview(state, stage_input.payload)
    quality_review = build_quality_review(cfg, stage_input.payload)
    write_quality_review(state, quality_review)
    write_run_summary(state, build_run_summary(state, stage_input.payload, quality_review))
    return state["run_id"]
