from __future__ import annotations

from ai_mv.core.artifacts.publish import write_pipeline_artifacts
from ai_mv.core.contracts.stage_io import StageInput
from ai_mv.core.orchestration.input_gate import validate_stage_input
from ai_mv.core.orchestration.scheduler import schedule
from ai_mv.core.orchestration.stage_runs import merge_stage_payload as _merge_stage_payload
from ai_mv.core.orchestration.stage_runs import PROTECTED_PAYLOAD_KEYS
from ai_mv.core.orchestration.stage_runs import run_result_stage
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
