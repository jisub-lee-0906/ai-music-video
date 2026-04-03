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
from ai_mv.core.stages.backend_preview import build_backend_preview
from ai_mv.core.stages.director_plan import build_director_plan_preview_payload
from ai_mv.core.stages.lyrics_timeline import build_lyrics_timeline_preview_payload
from ai_mv.core.stages.render_plan import build_render_plan_preview_payload
from ai_mv.core.stages.scene_plan import build_scene_plan_preview_payload


def run_preflight(config: dict, run_id: str = "", allow_existing_run: bool = False) -> str:
    cfg = dict(config)
    state = init_run_state(cfg, run_id, allow_existing=allow_existing_run, scope="preflight")
    payload = {
        "selected_brief": str(cfg.get("brief", "")).strip(),
        "story_profile": build_director_brief_intent(cfg),
        "workflow_inputs": {},
    }
    save_snapshot(state, payload)
    stage_input = StageInput(run_id=state["run_id"], config=cfg, payload=payload)
    try:
        _run_stage(state, stage_input, "acestep_music", _add_audio)
        _run_stage(state, stage_input, "lyrics_timeline", _add_lyrics_timeline)
        _run_stage(state, stage_input, "scene_outline", _add_scene_plan)
        _run_stage(state, stage_input, "direction_plan", _add_director_plan)
        _run_stage(state, stage_input, "prompt_plan", _add_render_plan)
        _run_stage(state, stage_input, "backend_preview", _add_backend_preview)
        state["current_stage"] = "preflight"
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


def _add_scene_plan(stage_input: StageInput) -> None:
    stage_input.payload.update(build_scene_plan_preview_payload(stage_input.config, stage_input.payload))


def _add_director_plan(stage_input: StageInput) -> None:
    stage_input.payload.update(build_director_plan_preview_payload(stage_input.config, stage_input.payload))


def _add_render_plan(stage_input: StageInput) -> None:
    stage_input.payload.update(build_render_plan_preview_payload(stage_input.config, stage_input.payload))


def _add_backend_preview(stage_input: StageInput) -> None:
    workflow_inputs = dict(stage_input.payload.get("workflow_inputs", {}))
    preview = build_backend_preview(stage_input.config, stage_input.payload)
    workflow_inputs["backend_preview"] = preview
    stage_input.payload.update(
        {
            "backend_preview": preview,
            "workflow_inputs": workflow_inputs,
        }
    )
