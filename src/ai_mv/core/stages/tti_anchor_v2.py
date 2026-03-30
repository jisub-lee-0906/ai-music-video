from __future__ import annotations

from ai_mv.core.contracts.stage_io import StageInput, StageOutput
from ai_mv.core.director_brief import build_director_brief_intent
from ai_mv.core.stages.payload_views import merge_planner_prompt
from ai_mv.engines.flux_2_dev_tti.runner import run_tti


def run_tti_anchor_v2(stage_input: StageInput) -> StageOutput:
    plan = build_tti_anchor_v2_plan(stage_input.config, stage_input.payload)
    anchors = run_tti(stage_input.config, plan)
    master_anchor = str(anchors[0]["identity_anchor"]) if anchors else ""
    workflow_v2 = dict(stage_input.payload.get("workflow_inputs_v2", {}))
    workflow_v2["tti_anchor_v2"] = {
        "master_prompt": str(plan["master_anchor"]["prompt_text"]),
        "shot_count": len(plan["shots"]),
        "master_anchor": master_anchor,
    }
    return StageOutput(
        "tti_anchor_v2",
        "done",
        {
            "anchors": anchors,
            "master_anchor_v2": master_anchor,
            "workflow_inputs_v2": workflow_v2,
            "planner_prompts": merge_planner_prompt(
                stage_input.payload,
                "tti_anchor_v2",
                {"prompt": str(plan["master_anchor"]["prompt_text"])},
            ),
        },
        [],
    )


def build_tti_anchor_v2_plan(config: dict, payload: dict) -> dict:
    brief = build_director_brief_intent(config)
    shots = [row for row in payload.get("render_plan_v2", {}).get("shot_packages", []) if isinstance(row, dict)]
    durations = _beat_duration_map(payload)
    tti_shots: list[dict] = []
    for idx, shot in enumerate(shots, start=1):
        shot_id = str(shot.get("shot_id", "")).strip()
        section_label = str(shot.get("section_label", "")).strip()
        duration = float(durations.get(shot_id, 2.0))
        tti_shots.append(
            {
                "shot_id": shot_id,
                "shot_type": _shot_type(shot),
                "section_name": str(shot.get("section_name", "")).strip(),
                "section_label": section_label,
                "duration_sec": duration,
                "is_chorus": "chorus" in section_label.lower(),
                "lyric_beat_id": shot_id,
                "line_refs": list(shot.get("line_refs", [])),
                "literal_image": str(shot.get("environment_anchor", "")).strip(),
                "symbolic_image": str(shot.get("motif_family", "")).strip(),
                "motif_object": str(shot.get("motif_family", "")).strip(),
                "edit_device": str(shot.get("story_role", "")).strip(),
                "prompt_focus": _prompt_focus(shot),
                "space_event": str(shot.get("environment_anchor", "")).strip(),
                "continuity_lock": str(shot.get("identity_core", "")).strip(),
                "scene_change_level": "evolve",
                "anchor_strategy": "refine_anchor",
                "continuity_basis": "heroine",
                "edit_role": str(shot.get("story_role", "")).strip(),
                "camera_language": str(shot.get("camera_intent", "")).strip(),
                "pose_delta": str(shot.get("performance_intent", "")).strip(),
                "emotion": str(shot.get("transition_intent", "")).strip(),
                "scene_detail": str(shot.get("environment_anchor", "")).strip(),
                "motion_hint": str(shot.get("motion_intent", "")).strip(),
                "workflow_motion_clause": str(shot.get("motion_intent", "")).strip(),
                "space_relation": str(shot.get("zone", "")).strip(),
                "start_frame": {},
                "end_frame": {},
                "kinetic_transition": "carry",
                "lighting_fx": str(shot.get("lighting_intent", "")).strip(),
                "kinetic_intensity": _kinetic_intensity(shot),
                "location_family": str(shot.get("motif_family", "")).strip(),
                "composition_shape": str(shot.get("camera_intent", "")).strip(),
                "palette_mode": str(brief.get("lighting_bias", "")).strip(),
                "character_render_mode": "cinematic heroine continuity",
                "face_exposure_level": "soft" if "chorus" in section_label.lower() else "partial",
                "heroine_visibility": "clear",
                "continuity_priority": "high",
                "wardrobe_read": "high",
                "hero_frame_score": 2,
                "consistency_need": "high",
                "mv_function": str(shot.get("story_role", "")).strip(),
                "return_weight": 2,
                "edit_density": "medium",
                "shot_priority": "support",
                "transition_role": "carry",
                "seed": idx,
                "retry": 0,
            }
        )
    master_prompt = build_tti_anchor_v2_master_prompt(config)
    return {
        "master_anchor": {
            "prompt_text": master_prompt,
            "seed": 1,
            "kinetic_transition": "anchor",
        },
        "shots": tti_shots,
    }


def build_tti_anchor_v2_master_prompt(config: dict) -> str:
    brief = build_director_brief_intent(config)
    hooks = ", ".join(brief.get("identity_hooks", []))
    wardrobe_guidance = str(brief.get("anchor_wardrobe_guidance", "")).strip()
    anchor_avoid = str(brief.get("anchor_avoid", "")).strip()
    return (
        f"{brief['style_contract']}. "
        f"{brief['identity_core']}. "
        f"Identity hooks: {hooks}. "
        "A premium heroine reference image for continuity-sensitive music video production. "
        "High-end casting and wardrobe reference, polished beauty detail, realistic skin detail, and one memorable silhouette cue. "
        "Three-quarter full-body presentation pose with a slight body turn, calm approachable expression, direct readable face, both hands visible, full outfit visible, and unobstructed leg line. "
        "Polished everyday idol wardrobe must read clearly with clean seam lines, premium fabric response, and one small signature accent. "
        f"{wardrobe_guidance} "
        f"{anchor_avoid} "
        "Keep the hairline, bangs, jawline, shoulders, waist, shoes, and overall silhouette clearly readable for downstream reference matching. "
        "The background is a pale grey premium studio backdrop with soft controlled lighting, gentle floor shadow, and no props or environmental clutter. "
        "Production-ready hero reference, continuity anchor image, high-end music video casting still."
    )


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


def _shot_type(shot: dict) -> str:
    role = str(shot.get("story_role", "")).lower()
    zone = str(shot.get("zone", "")).lower()
    if "peak" in role or "peak" in zone:
        return "WORLD_EVENT"
    if "bridge" in role or zone == "compression":
        return "GRAPHIC_EVENT"
    if "threshold" in role or zone in {"threshold", "edge"}:
        return "ENV_TRANSITION"
    return "DETAIL_INSERT"


def _prompt_focus(shot: dict) -> str:
    zone = str(shot.get("zone", "")).lower()
    if zone in {"open_world", "open_world_peak"}:
        return "space"
    if zone == "compression":
        return "graphic"
    return "object"


def _kinetic_intensity(shot: dict) -> str:
    section = str(shot.get("section_label", "")).lower()
    if "final chorus" in section or "chorus" in section:
        return "high"
    if "bridge" in section:
        return "medium"
    return "low"
