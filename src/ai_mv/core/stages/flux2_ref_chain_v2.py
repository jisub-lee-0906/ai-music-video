from __future__ import annotations

from ai_mv.core.contracts.stage_io import StageInput, StageOutput
from ai_mv.core.stages.payload_views import merge_planner_prompt
from ai_mv.engines.flux_2_dev_ref.runner import run_flux2_ref


def run_flux2_ref_chain_v2(stage_input: StageInput) -> StageOutput:
    plan = build_flux2_ref_plan_v2(stage_input.payload)
    flux2_ref_images = run_flux2_ref(stage_input.config, plan) if plan["items"] else []
    clip_routes = _clip_routes_from_v2(stage_input.payload, flux2_ref_images)
    workflow_v2 = dict(stage_input.payload.get("workflow_inputs_v2", {}))
    workflow_v2["flux2_ref_chain_v2"] = {
        "item_count": len(plan["items"]),
        "items": [
            {"shot_id": str(item["shot_id"]), "prompt_text": str(item["prompt_text"])}
            for item in plan["items"]
        ],
    }
    return StageOutput(
        "flux2_ref_chain_v2",
        "done",
        {
            "flux2_ref_images": flux2_ref_images,
            "clip_routes": clip_routes,
            "workflow_inputs_v2": workflow_v2,
            "planner_prompts": merge_planner_prompt(
                stage_input.payload,
                "flux2_ref_chain_v2",
                {"prompt": "Render scene-specific Flux2 reference start/end images from the v2 director plan while preserving the same heroine."},
            ),
        },
        [],
    )


def build_flux2_ref_plan_v2(payload: dict) -> dict:
    shots = [row for row in payload.get("render_plan_v2", {}).get("shot_packages", []) if isinstance(row, dict)]
    master_anchor = str(payload.get("master_anchor_v2", "")).strip()
    durations = _beat_duration_map(payload)
    items: list[dict] = []
    for idx, shot in enumerate(shots, start=1):
        shot_id = str(shot.get("shot_id", "")).strip()
        duration = float(durations.get(shot_id, 2.0))
        prompt_text = (
            f"The same Korean female idol, now {_action_from_shot(shot)} inside {shot['environment_anchor']}. "
            f"{_sentence(shot['camera_intent'])} "
            "Cinematic live-action still frame, natural skin response, grounded environmental realism."
        )
        items.append(
            {
                "shot_id": shot_id,
                "chain_key": f"{shot_id}:{idx}",
                "timeline_index": idx,
                "anchor": master_anchor,
                "ref": master_anchor,
                "style_ref": "",
                "prompt_text": prompt_text,
                "style_clause": "",
                "subject_clause": "The same Korean female idol",
                "action_clause": f"now {_action_from_shot(shot)} inside {shot['environment_anchor']}",
                "camera_clause": str(shot.get("camera_intent", "")).strip(),
                "environment_clause": "",
                "continuity_clause": "Cinematic live-action still frame, natural skin response, grounded environmental realism.",
                "duration_sec": duration,
                "clip_index": idx,
                "clip_count": len(shots),
                "clip_phase": "establish" if idx == 1 else ("resolve" if idx == len(shots) else "advance"),
                "shot_type": "DETAIL_INSERT",
                "section_name": str(shot.get("section_name", "")).strip(),
                "section_label": str(shot.get("section_label", "")).strip(),
                "is_chorus": "chorus" in str(shot.get("section_label", "")).lower(),
                "camera_language": str(shot.get("camera_intent", "")).strip(),
                "pose_delta": str(shot.get("performance_intent", "")).strip(),
                "emotion": str(shot.get("transition_intent", "")).strip(),
                "scene_detail": str(shot.get("environment_anchor", "")).strip(),
                "motion_hint": str(shot.get("motion_intent", "")).strip(),
                "space_relation": str(shot.get("zone", "")).strip(),
                "kinetic_transition": "carry",
                "lighting_fx": str(shot.get("lighting_intent", "")).strip(),
                "kinetic_intensity": "medium",
                "route_reason": "v2_ref_pair",
                "scene_change_level": "evolve",
                "anchor_strategy": "refine_anchor",
                "continuity_basis": "heroine",
            }
        )
    return {"items": items}


def _clip_routes_from_v2(payload: dict, flux2_ref_images: list[dict]) -> list[dict]:
    shots = [row for row in payload.get("render_plan_v2", {}).get("shot_packages", []) if isinstance(row, dict)]
    durations = _beat_duration_map(payload)
    ref_map = {str(row.get("shot_id", "")).strip(): row for row in flux2_ref_images if isinstance(row, dict)}
    routes: list[dict] = []
    for idx, shot in enumerate(shots, start=1):
        shot_id = str(shot.get("shot_id", "")).strip()
        ref_row = ref_map.get(shot_id, {})
        routes.append(
            {
                "shot_id": shot_id,
                "lyric_beat_id": shot_id,
                "anchor": str(payload.get("master_anchor_v2", "")).strip(),
                "duration_sec": float(durations.get(shot_id, 2.0)),
                "use_ref": True,
                "route_reason": "v2_ref_pair",
                "mv_function": str(shot.get("story_role", "")).strip(),
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
                "start": str(ref_row.get("start", "")),
                "end": str(ref_row.get("end", "")),
            }
        )
    return routes


def _action_from_shot(shot: dict) -> str:
    action = str(shot.get("performance_intent", "")).strip().rstrip(".")
    lower = action.lower()
    prefix = "preserve the same heroine while centering the visible action:"
    if lower.startswith(prefix):
        action = action[len(prefix):].strip()
    return action or "shifts into the next readable pose"


def _sentence(text: str) -> str:
    cleaned = " ".join(str(text).strip().rstrip(". ").split())
    return f"{cleaned}." if cleaned else ""


def _beat_duration_map(payload: dict) -> dict[str, float]:
    out: dict[str, float] = {}
    timeline = payload.get("lyrics_timeline", {})
    for section in timeline.get("sections", []):
        if not isinstance(section, dict):
            continue
        for beat in section.get("lyric_beats", []):
            if not isinstance(beat, dict):
                continue
            beat_id = str(beat.get("beat_id", "")).strip()
            if not beat_id:
                continue
            start = float(beat.get("start_sec", 0.0) or 0.0)
            end = float(beat.get("end_sec", 0.0) or 0.0)
            out[beat_id] = max(0.5, end - start) if end > start else 2.0
    return out
