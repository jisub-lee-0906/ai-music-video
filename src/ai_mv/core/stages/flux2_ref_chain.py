from __future__ import annotations

from ai_mv.core.contracts.stage_io import StageInput, StageOutput
from ai_mv.core.director_brief import build_director_brief_intent
from ai_mv.core.stages.payload_views import merge_planner_prompt
from ai_mv.engines.flux_2_dev_ref.runner import run_flux2_ref


def run_flux2_ref_chain(stage_input: StageInput) -> StageOutput:
    plan = build_flux2_ref_plan(stage_input.config, stage_input.payload)
    flux2_ref_images = run_flux2_ref(stage_input.config, plan) if plan["items"] else []
    clip_routes = _clip_routes_from_prompt_plan(stage_input.payload, flux2_ref_images)
    workflow_inputs = dict(stage_input.payload.get("workflow_inputs", {}))
    workflow_inputs["flux2_ref_chain"] = {
        "item_count": len(plan["items"]),
        "items": [{"shot_id": str(item["shot_id"]), "prompt_text": str(item["prompt_text"])} for item in plan["items"]],
    }
    return StageOutput(
        "flux2_ref_chain",
        "done",
        {
            "flux2_ref_images": flux2_ref_images,
            "clip_routes": clip_routes,
            "workflow_inputs": workflow_inputs,
            "planner_prompts": merge_planner_prompt(
                stage_input.payload,
                "flux2_ref_chain",
                {"prompt": "Render scene-specific Flux2 reference images from prompt_plan while preserving the same heroine."},
            ),
        },
        [],
    )


def build_flux2_ref_plan(config: dict, payload: dict) -> dict:
    brief = build_director_brief_intent(config)
    shots = [row for row in payload.get("prompt_plan", {}).get("ref_items", []) if isinstance(row, dict)]
    master_anchor = str(payload.get("master_anchor", "")).strip()
    items: list[dict] = []
    for idx, shot in enumerate(shots, start=1):
        items.append(
            {
                "shot_id": str(shot.get("shot_id", "")).strip(),
                "chain_key": f"{shot.get('shot_id', '')}:{idx}",
                "timeline_index": idx,
                "anchor": master_anchor,
                "ref": master_anchor,
                "style_ref": "",
                "prompt_text": str(shot.get("ref_end_prompt_text", "")).strip(),
                "start_prompt_text": str(shot.get("ref_start_prompt_text", "")).strip(),
                "end_prompt_text": str(shot.get("ref_end_prompt_text", "")).strip(),
                "style_clause": "",
                "subject_clause": str(brief.get("ref_subject_intro", "")).strip(),
                "action_clause": "",
                "camera_clause": "",
                "environment_clause": "",
                "duration_sec": float(shot.get("duration_sec", 2.0) or 2.0),
                "clip_index": idx,
                "clip_count": len(shots),
                "clip_phase": "establish" if idx == 1 else ("resolve" if idx == len(shots) else "advance"),
                "shot_type": "DETAIL_INSERT",
                "section_name": str(shot.get("section_name", "")).strip(),
                "section_label": str(shot.get("section_label", "")).strip(),
                "is_chorus": "chorus" in str(shot.get("section_label", "")).lower(),
                "camera_language": "",
                "pose_delta": str(shot.get("dominant_action", "")).strip(),
                "emotion": str(shot.get("continuity_delta", "")).strip(),
                "scene_detail": _literal_scene_description(shot),
                "environment_family": str(shot.get("ref_archetype", "")).strip(),
                "camera_distance_band": "",
                "contact_intent": str(shot.get("content_trace", "")).strip(),
                "motion_hint": str(shot.get("dominant_action", "")).strip(),
                "space_relation": str(shot.get("world_zone", "")).strip(),
                "kinetic_transition": "carry",
                "lighting_fx": "",
                "kinetic_intensity": "medium",
                "route_reason": "ref_pair",
                "scene_change_level": "evolve",
                "anchor_strategy": "refine_anchor",
                "continuity_basis": "heroine",
            }
        )
    return {"items": items}


def _clip_routes_from_prompt_plan(payload: dict, flux2_ref_images: list[dict]) -> list[dict]:
    shots = [row for row in payload.get("prompt_plan", {}).get("ref_items", []) if isinstance(row, dict)]
    ref_map = {str(row.get("shot_id", "")).strip(): row for row in flux2_ref_images if isinstance(row, dict)}
    routes: list[dict] = []
    for idx, shot in enumerate(shots, start=1):
        shot_id = str(shot.get("shot_id", "")).strip()
        ref_row = ref_map.get(shot_id, {})
        routes.append(
            {
                "shot_id": shot_id,
                "lyric_beat_id": shot_id,
                "anchor": str(payload.get("master_anchor", "")).strip(),
                "duration_sec": float(shot.get("duration_sec", 2.0) or 2.0),
                "use_ref": True,
                "route_reason": "ref_pair",
                "mv_function": str(shot.get("story_goal", "")).strip(),
                "hero_frame_score": 2,
                "consistency_need": "high",
                "section_name": str(shot.get("section_name", "")).strip(),
                "section_label": str(shot.get("section_label", "")).strip(),
                "prompt_focus": "space",
                "face_exposure_level": "soft",
                "continuity_priority": "high",
                "clip_index": idx,
                "clip_count": len(shots),
                "timeline_index": idx,
                "chain_key": f"{shot_id}:{idx}",
                "end": str(ref_row.get("end", "")),
            }
        )
    return routes


def _literal_scene_description(shot: dict) -> str:
    primary_surface = " ".join(str(shot.get("primary_surface", "")).strip().rstrip(".").split())
    if primary_surface:
        return primary_surface
    trace = " ".join(str(shot.get("content_trace", "")).strip().rstrip(".").split())
    if trace:
        return f"a readable station-side place at night with {trace}"
    return "a readable station-side place at night with clear physical depth around her"
