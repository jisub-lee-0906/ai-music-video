from __future__ import annotations

import traceback

from ai_mv.utils.redaction import redact_secrets

from ai_mv.core.artifacts.publish import write_pipeline_artifacts
from ai_mv.core.contracts.stage_io import StageInput
from ai_mv.core.orchestration.input_gate import validate_stage_input
from ai_mv.core.orchestration.stage_runs import run_preview_stage
from ai_mv.core.state.state_snapshot import save_snapshot
from ai_mv.core.state.state_store import init_run_state
from ai_mv.core.stages.acestep_music import build_audio_preview_payload
from ai_mv.core.stages.plan_mv import build_plan_preview_payload


def run_preflight(config: dict, run_id: str = "", allow_existing_run: bool = False) -> str:
    cfg = dict(config)
    state = init_run_state(cfg, run_id, allow_existing=allow_existing_run, scope="preflight")
    payload = {
        "concept_text": str(cfg.get("concept_text", "")).strip(),
        "workflow_inputs": {},
    }
    save_snapshot(state, payload)
    stage_input = StageInput(run_id=state["run_id"], config=cfg, payload=payload)
    try:
        _run_stage(state, stage_input, "audio", _add_audio)
        _run_stage(state, stage_input, "plan", _add_plan)
        state["current_stage"] = "preflight"
        state["status"] = "done"
    except Exception as exc:
        state["status"] = "failed"
        state["failure_reason"] = redact_secrets(f"{state['current_stage']}: {exc}" if state["current_stage"] else str(exc))
        state["failure_traceback"] = redact_secrets(traceback.format_exc())
        save_snapshot(state, stage_input.payload)
        write_pipeline_artifacts(state, stage_input.payload, cfg)
        raise
    save_snapshot(state, stage_input.payload)
    write_pipeline_artifacts(state, stage_input.payload, cfg)
    return state["run_id"]


def _run_stage(state: dict, stage_input: StageInput, name: str, fn) -> None:
    run_preview_stage(
        state,
        stage_input,
        name,
        fn,
        save_snapshot=save_snapshot,
        validate_stage_input=validate_stage_input,
    )


def _add_audio(stage_input: StageInput) -> None:
    stage_input.payload.update(build_audio_preview_payload(stage_input.config, stage_input.payload, stage_input.run_id))


def _add_plan(stage_input: StageInput) -> None:
    stage_input.payload.update(build_plan_preview_payload(stage_input.config, stage_input.payload))
