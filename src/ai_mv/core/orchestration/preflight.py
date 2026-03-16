from __future__ import annotations

import traceback

from ai_mv.core.artifacts.manifest import write_manifest
from ai_mv.core.artifacts.prompt_preview import write_prompt_preview
from ai_mv.core.artifacts.quality_review import write_quality_review
from ai_mv.core.artifacts.run_summary import write_run_summary
from ai_mv.core.artifacts.summary import write_summary
from ai_mv.core.artifacts.workflow_inputs_preview import write_workflow_inputs_preview
from ai_mv.core.orchestration.input_gate import validate_stage_input
from ai_mv.core.contracts.stage_io import StageInput
from ai_mv.core.quality_review import build_quality_review, build_run_summary
from ai_mv.core.state.state_snapshot import save_snapshot
from ai_mv.core.state.state_store import init_run_state
from ai_mv.core.stages.acestep_music import build_audio_preview_payload
from ai_mv.core.stages.flux2_ref_chain import build_flux2_ref_preview_payload
from ai_mv.core.stages.shot_router import build_shot_router_preview_payload
from ai_mv.core.stages.shot_timeline import build_shot_timeline_preview_payload
from ai_mv.core.stages.wan_interpolation import build_wan_preview_payload
from ai_mv.engines.lyrics_timeline.planner import build_lyrics_timeline
from ai_mv.engines.lyrics_timeline.planner import build_lyrics_timeline_preview_prompt
from ai_mv.engines.visual_story_bible.planner import build_visual_story_bible
from ai_mv.engines.visual_story_bible.planner import build_visual_story_bible_preview_prompt


def run_preflight(config: dict, run_id: str = "", allow_existing_run: bool = False) -> str:
    cfg = dict(config)
    state = init_run_state(cfg, run_id, allow_existing=allow_existing_run, scope="preflight")
    payload = {"selected_profile": str(cfg.get("profile", "")).strip()}
    save_snapshot(state, payload)
    stage_input = StageInput(run_id=state["run_id"], config=cfg, payload=payload)
    try:
        _run_preflight_stage(state, stage_input, "acestep_music", _add_audio)
        _run_preflight_stage(state, stage_input, "lyrics_timeline", _add_lyrics_timeline)
        _run_preflight_stage(state, stage_input, "visual_story_bible", _add_story_bible)
        _run_preflight_stage(state, stage_input, "shot_timeline", _add_shot_timeline)
        _run_preflight_stage(state, stage_input, "shot_router", _add_shot_router)
        _run_preflight_stage(state, stage_input, "flux2_ref_chain", _add_flux2_ref)
        _run_preflight_stage(state, stage_input, "wan_interpolation", _add_wan)
        state["current_stage"] = "preflight"
        state["status"] = "done"
    except Exception as exc:
        state["status"] = "failed"
        state["failure_reason"] = f"{state['current_stage']}: {exc}" if state["current_stage"] else str(exc)
        state["failure_traceback"] = traceback.format_exc()
        save_snapshot(state, stage_input.payload)
        _write_preflight_artifacts(state, stage_input.payload, cfg)
        raise
    save_snapshot(state, stage_input.payload)
    _write_preflight_artifacts(state, stage_input.payload, cfg)
    return state["run_id"]


def _run_preflight_stage(state: dict, stage_input: StageInput, name: str, fn) -> None:
    state["current_stage"] = name
    save_snapshot(state, stage_input.payload)
    validate_stage_input(name, stage_input.payload)
    fn(stage_input)
    state["completed_stages"].append(name)
    save_snapshot(state, stage_input.payload)


def _add_audio(stage_input: StageInput) -> None:
    stage_input.payload.update(build_audio_preview_payload(stage_input.config, stage_input.payload, stage_input.run_id))


def _add_lyrics_timeline(stage_input: StageInput) -> None:
    timeline = build_lyrics_timeline(stage_input.config, stage_input.payload)
    stage_input.payload.update(
        {
            "lyrics_timeline": timeline,
            "render_inputs": dict(stage_input.payload.get("render_inputs", {}), lyrics_timeline=timeline),
            "planner_prompts": _merge(
                stage_input.payload,
                "lyrics_timeline",
                {"prompt": build_lyrics_timeline_preview_prompt(stage_input.payload["audio_plan"], stage_input.payload["audio_map"]["sections"])},
            ),
            "workflow_inputs_preview": _merge(stage_input.payload, "lyrics_timeline", {"sections": list(timeline.get("sections", []))}),
        }
    )


def _add_story_bible(stage_input: StageInput) -> None:
    story_bible = build_visual_story_bible(stage_input.config, stage_input.payload)
    stage_input.payload.update(
        {
            "visual_story_bible": story_bible,
            "render_inputs": dict(stage_input.payload.get("render_inputs", {}), visual_story_bible=story_bible),
            "planner_prompts": _merge(stage_input.payload, "visual_story_bible", {"prompt": build_visual_story_bible_preview_prompt(stage_input.config, stage_input.payload)}),
            "workflow_inputs_preview": _merge(stage_input.payload, "visual_story_bible", {"story_bible_preview": story_bible}),
        }
    )


def _add_shot_timeline(stage_input: StageInput) -> None:
    stage_input.payload.update(build_shot_timeline_preview_payload(stage_input.config, stage_input.payload))


def _add_shot_router(stage_input: StageInput) -> None:
    stage_input.payload.update(build_shot_router_preview_payload(stage_input.config, stage_input.payload))


def _add_flux2_ref(stage_input: StageInput) -> None:
    stage_input.payload.update(build_flux2_ref_preview_payload(stage_input.config, stage_input.payload))


def _add_wan(stage_input: StageInput) -> None:
    stage_input.payload.update(build_wan_preview_payload(stage_input.config, stage_input.payload))


def _merge(payload: dict, key: str, value: dict) -> dict:
    if key in {"audio", "lyrics_timeline", "visual_story_bible", "shot_timeline", "shot_router", "flux2_ref_chain", "wan_interpolation"}:
        root = "planner_prompts" if "prompt" in value or "batches" in value else "workflow_inputs_preview"
        out = dict(payload.get(root, {}))
        out[key] = value
        return out
    raise RuntimeError(f"unsupported preview key: {key}")


def _write_preflight_artifacts(state: dict, payload: dict, config: dict) -> None:
    write_manifest(state, payload)
    write_summary(state, payload)
    write_prompt_preview(state, payload)
    write_workflow_inputs_preview(state, payload)
    quality_review = build_quality_review(config, payload)
    write_quality_review(state, quality_review)
    write_run_summary(state, build_run_summary(state, payload, quality_review))
