from __future__ import annotations

import traceback

from ai_mv.core.artifacts.dashboard import write_dashboard
from ai_mv.core.artifacts.manifest import write_manifest
from ai_mv.core.artifacts.summary import write_summary
from ai_mv.core.contracts.stage_io import StageInput
from ai_mv.core.orchestration.input_gate import validate_stage_input
from ai_mv.core.orchestration.scheduler import schedule
from ai_mv.core.quality.release_readiness import readiness_report
from ai_mv.core.state.state_snapshot import save_snapshot
from ai_mv.core.state.state_store import init_run_state, load_config


def run_pipeline(config_path: str, run_id: str = "") -> str:
    cfg = load_config(config_path)
    state = init_run_state(cfg, run_id)
    stage_input = StageInput(run_id=state["run_id"], config=cfg, payload={})

    for name, stage_fn in schedule():
        state["current_stage"] = name
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
    write_dashboard(state, stage_input.payload)
    readiness_report(state, stage_input.payload)
    return state["run_id"]
