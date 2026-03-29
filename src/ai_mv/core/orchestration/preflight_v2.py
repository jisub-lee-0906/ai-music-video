from __future__ import annotations

import traceback

from ai_mv.core.artifacts.publish import write_pipeline_artifacts
from ai_mv.core.contracts.stage_io import StageInput
from ai_mv.core.director_brief import build_director_brief_intent
from ai_mv.core.orchestration.input_gate import validate_stage_input
from ai_mv.core.orchestration.stage_runs import run_preview_stage
from ai_mv.core.state.state_snapshot import save_snapshot
from ai_mv.core.state.state_store import init_run_state
from ai_mv.core.stages.acestep_music import build_audio_preview_payload
from ai_mv.core.stages.backend_preview_v2 import build_backend_preview_v2
from ai_mv.core.stages.director_plan_v2 import build_director_plan_v2_preview_payload
from ai_mv.core.stages.lyrics_timeline import build_lyrics_timeline_preview_payload
from ai_mv.core.stages.render_plan_v2 import build_render_plan_v2_preview_payload
from ai_mv.core.stages.scene_plan_v2 import build_scene_plan_v2_preview_payload


def run_preflight_v2(config: dict, run_id: str = "", allow_existing_run: bool = False) -> str:
    cfg = dict(config)
    state = init_run_state(cfg, run_id, allow_existing=allow_existing_run, scope="preflight")
    payload = {
        "selected_brief": str(cfg.get("brief", "")).strip(),
        "director_brief_intent": build_director_brief_intent(cfg),
        "workflow_inputs_v2": {},
    }
    save_snapshot(state, payload)
    stage_input = StageInput(run_id=state["run_id"], config=cfg, payload=payload)
    try:
        _run_stage(state, stage_input, "acestep_music", _add_audio)
        _run_stage(state, stage_input, "lyrics_timeline", _add_lyrics_timeline)
        _run_stage(state, stage_input, "scene_plan_v2", _add_scene_plan_v2)
        _run_stage(state, stage_input, "director_plan_v2", _add_director_plan_v2)
        _run_stage(state, stage_input, "render_plan_v2", _add_render_plan_v2)
        _run_stage(state, stage_input, "backend_preview_v2", _add_backend_preview_v2)
        state["current_stage"] = "preflight-v2"
        state["status"] = "done"
    except Exception as exc:
        state["status"] = "failed"
        state["failure_reason"] = f"{state['current_stage']}: {exc}" if state["current_stage"] else str(exc)
        state["failure_traceback"] = traceback.format_exc()
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


def _add_lyrics_timeline(stage_input: StageInput) -> None:
    stage_input.payload.update(build_lyrics_timeline_preview_payload(stage_input.config, stage_input.payload))


def _add_scene_plan_v2(stage_input: StageInput) -> None:
    stage_input.payload.update(build_scene_plan_v2_preview_payload(stage_input.config, stage_input.payload))


def _add_director_plan_v2(stage_input: StageInput) -> None:
    stage_input.payload.update(build_director_plan_v2_preview_payload(stage_input.config, stage_input.payload))


def _add_render_plan_v2(stage_input: StageInput) -> None:
    stage_input.payload.update(build_render_plan_v2_preview_payload(stage_input.config, stage_input.payload))


def _add_backend_preview_v2(stage_input: StageInput) -> None:
    workflow_v2 = dict(stage_input.payload.get("workflow_inputs_v2", {}))
    preview = build_backend_preview_v2(stage_input.config, stage_input.payload)
    workflow_v2["backend_preview_v2"] = preview
    stage_input.payload.update(
        {
            "backend_preview_v2": preview,
            "workflow_inputs_v2": workflow_v2,
        }
    )
