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
from ai_mv.core.visual_pipeline import build_mv_directives, build_section_semantics
from ai_mv.engines.acestep_1_5_split.planner import _audio_prompt, build_audio_plan
from ai_mv.engines.acestep_1_5_split.runner import _sections
from ai_mv.engines.flux2_reference.planner import build_flux2_ref_plan
from ai_mv.engines.flux_1_dev_tti.planner import build_tti_plan
from ai_mv.engines.flux_1_dev_tti.runner import _pack_anchor
from ai_mv.engines.visual_bridge.planner import build_visual_brief
from ai_mv.engines.wan_2_2_flf2v.planner import build_wan_plan


def run_preflight(config: dict, run_id: str = "", allow_existing_run: bool = False) -> str:
    cfg = dict(config)
    state = init_run_state(cfg, run_id, allow_existing=allow_existing_run, scope="preflight")
    payload = {"selected_profile": str(cfg.get("profile", "")).strip()}
    save_snapshot(state, payload)
    stage_input = StageInput(run_id=state["run_id"], config=cfg, payload=payload)
    try:
        _run_preflight_stage(state, stage_input, "acestep_music", _add_audio)
        _run_preflight_stage(state, stage_input, "visual_bridge", _add_visual)
        _run_preflight_stage(state, stage_input, "tti_anchor", _add_tti)
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
    plan = build_audio_plan(stage_input.config, dict(stage_input.payload, run_id=stage_input.run_id))
    audio_map = _preflight_audio_map(plan)
    audio_map.update(_audio_context(stage_input.config, audio_map, plan))
    stage_input.payload.update(
        {
            "profile_intent": dict(plan.get("profile_intent", {})),
            "audio_plan": dict(plan),
            "audio_map": audio_map,
            "music_file": "",
            "planner_prompts": _merge(stage_input.payload, "audio", {"prompt": _audio_prompt(plan)}),
            "workflow_inputs_preview": _merge(
                stage_input.payload,
                "audio",
                {"text_inputs": _audio_inputs(stage_input.config, plan)},
            ),
        }
    )


def _add_visual(stage_input: StageInput) -> None:
    brief = build_visual_brief(stage_input.config, stage_input.payload)
    stage_input.payload.update(
        {
            "visual_brief": brief,
            "render_inputs": dict(stage_input.payload.get("render_inputs", {}), visual_brief=brief),
            "planner_prompts": _merge(
                stage_input.payload,
                "visual_bridge",
                {"prompt": _visual_prompt(stage_input.payload["audio_map"])},
            ),
        }
    )


def _add_tti(stage_input: StageInput) -> None:
    from ai_mv.core.stages.tti_anchor import _tti_prompt, _tti_workflow_input

    plan = build_tti_plan(stage_input.config, stage_input.payload)
    anchors = [_pack_anchor(shot, "preflight://anchor/master.png") for shot in plan["shots"]]
    stage_input.payload.update(
        {
            "anchors": anchors,
            "shot_plan": {"master_anchor": dict(plan["master_anchor"]), "shots": list(plan["shots"])},
            "render_inputs": dict(stage_input.payload.get("render_inputs", {}), shot_plan={"master_anchor": dict(plan["master_anchor"]), "shots": list(plan["shots"])}),
            "planner_prompts": _merge(stage_input.payload, "tti_anchor", {"prompt": _tti_prompt(stage_input, plan)}),
            "workflow_inputs_preview": _merge(
                stage_input.payload,
                "tti_anchor",
                {"master_anchor": _tti_workflow_input(stage_input.config, plan["master_anchor"])},
            ),
        }
    )


def _add_shot_router(stage_input: StageInput) -> None:
    from ai_mv.core.stages.shot_router import _route_policy_summary, _route_preview, build_shot_routes

    routes = build_shot_routes(stage_input.config, stage_input.payload)
    stage_input.payload.update(
        {
            "clip_routes": routes,
            "render_inputs": dict(stage_input.payload.get("render_inputs", {}), clip_routes=routes),
            "planner_prompts": _merge(stage_input.payload, "shot_router", {"prompt": _route_policy_summary(stage_input.config)}),
            "workflow_inputs_preview": _merge(
                stage_input.payload,
                "shot_router",
                {"decisions": _route_preview(routes)},
            ),
        }
    )


def _add_flux2_ref(stage_input: StageInput) -> None:
    from ai_mv.core.stages.flux2_ref_chain import _flux2_ref_prompt_batches, _flux2_ref_workflow_inputs

    plan = build_flux2_ref_plan(stage_input.config, stage_input.payload)
    flux2_ref_images = [_preflight_flux2_ref_item(item) for item in plan["items"]]
    stage_input.payload.update(
        {
            "flux2_ref_images": flux2_ref_images,
            "render_inputs": dict(stage_input.payload.get("render_inputs", {}), flux2_ref_images=flux2_ref_images),
            "planner_prompts": _merge(stage_input.payload, "flux2_ref_chain", {"batches": _flux2_ref_prompt_batches(stage_input, plan)}),
            "workflow_inputs_preview": _merge(
                stage_input.payload,
                "flux2_ref_chain",
                {"items": _flux2_ref_workflow_inputs(stage_input.config, plan["items"])},
            ),
        }
    )


def _add_wan(stage_input: StageInput) -> None:
    from ai_mv.core.stages.wan_interpolation import _wan_prompt_batches, _wan_workflow_inputs

    plan = build_wan_plan(stage_input.config, stage_input.payload)
    stage_input.payload.update(
        {
            "clips": list(plan["clips"]),
            "render_inputs": dict(stage_input.payload.get("render_inputs", {}), clips=list(plan["clips"])),
            "planner_prompts": _merge(stage_input.payload, "wan_interpolation", {"batches": _wan_prompt_batches(stage_input, plan)}),
            "workflow_inputs_preview": _merge(
                stage_input.payload,
                "wan_interpolation",
                {"clips": _wan_workflow_inputs(stage_input.config, plan["clips"])},
            ),
        }
    )


def _preflight_audio_map(plan: dict) -> dict:
    duration = float(plan["duration"])
    return {
        "duration_sec": duration,
        "bpm_estimate": int(plan["bpm"]),
        "sections": _sections(
            duration,
            plan.get("lyrics_blocks", []),
            int(plan.get("bpm", 0)),
            int(plan.get("beats_per_bar", 4)),
            plan.get("section_bars", {}),
        ),
        "music_file": "",
    }


def _audio_context(config: dict, audio_map: dict, plan: dict) -> dict:
    return {
        "genre_description": str(plan.get("genre_description", "")).strip(),
        "lyrics": str(plan.get("lyrics", "")).strip(),
        "tags": str(plan.get("tags", "")).strip(),
        "profile_intent": dict(plan.get("profile_intent", {})),
        "style_guidance": str(plan.get("style_guidance", "")).strip(),
        "language": str(plan.get("language", "")).strip(),
        "profile_summary": str(plan.get("profile_summary", "")).strip(),
        "audio_direction": str(plan.get("audio_direction", "")).strip(),
        "hook_direction": str(plan.get("hook_direction", "")).strip(),
        "visual_direction": str(plan.get("visual_direction", "")).strip(),
        "negative_direction": str(plan.get("negative_direction", "")).strip(),
        "section_semantics": build_section_semantics(config, list(audio_map.get("sections", []))),
        "mv_directives": build_mv_directives(config),
    }


def _audio_inputs(config: dict, plan: dict) -> dict:
    from ai_mv.engines.acestep_1_5_split.mapper import AUDIO_TEXT, map_audio_workflow

    wf = map_audio_workflow(config, plan)
    return dict(wf["node.inputs"][AUDIO_TEXT])


def _visual_prompt(audio_map: dict) -> str:
    from ai_mv.engines.visual_bridge.planner import _planner_prompt

    return _planner_prompt({}, audio_map, list(audio_map["sections"]))


def _preflight_flux2_ref_item(item: dict) -> dict:
    out = dict(item)
    sid = str(item["shot_id"])
    out["start"] = f"preflight://flux2_ref/{sid}_start.png"
    out["end"] = f"preflight://flux2_ref/{sid}_end.png"
    return out


def _merge(payload: dict, key: str, value: dict) -> dict:
    if key in {"audio", "visual_bridge", "tti_anchor", "shot_router", "flux2_ref_chain", "wan_interpolation"}:
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
