from __future__ import annotations

from ai_mv.core.contracts.stage_io import StageInput, StageOutput
from ai_mv.core.director_brief import build_director_brief_intent
from ai_mv.core.prompt_grammar import tti_anchor_families
from ai_mv.core.stages.payload_views import merge_planner_prompt
from ai_mv.engines.flux_2_dev_tti.runner import run_tti


def run_tti_anchor(stage_input: StageInput) -> StageOutput:
    plan = build_tti_anchor_plan(stage_input.config, stage_input.payload)
    anchors = run_tti(stage_input.config, plan)
    master_anchor = str(anchors[0]["identity_anchor"]) if anchors else ""
    workflow_inputs = dict(stage_input.payload.get("workflow_inputs", {}))
    workflow_inputs["tti_anchor"] = {
        "master_prompt": str(plan["master_anchor"]["prompt_text"]),
        "shot_count": len(plan["shots"]),
        "master_anchor": master_anchor,
    }
    return StageOutput(
        "tti_anchor",
        "done",
        {
            "anchors": anchors,
            "master_anchor": master_anchor,
            "workflow_inputs": workflow_inputs,
            "planner_prompts": merge_planner_prompt(
                stage_input.payload,
                "tti_anchor",
                {"prompt": str(plan["master_anchor"]["prompt_text"])},
            ),
        },
        [],
    )


def build_tti_anchor_plan(config: dict, payload: dict) -> dict:
    brief = build_director_brief_intent(config)
    shots = [row for row in payload.get("prompt_plan", {}).get("ref_items", []) if isinstance(row, dict)]
    tti_shots = []
    for idx, shot in enumerate(shots, start=1):
        section_label = str(shot.get("section_label", "")).strip()
        tti_shots.append(
            {
                "shot_id": str(shot.get("shot_id", "")).strip(),
                "shot_type": "DETAIL_INSERT",
                "section_name": str(shot.get("section_name", "")).strip(),
                "section_label": section_label,
                "duration_sec": float(shot.get("duration_sec", 2.0) or 2.0),
                "is_chorus": "chorus" in section_label.lower(),
                "lyric_beat_id": str(shot.get("shot_id", "")).strip(),
                "line_refs": list(shot.get("line_refs", [])),
                "literal_image": str(shot.get("primary_surface", "")).strip(),
                "symbolic_image": str(shot.get("ref_archetype", "")).strip(),
                "motif_object": str(shot.get("ref_archetype", "")).strip(),
                "edit_device": str(shot.get("story_goal", "")).strip(),
                "prompt_focus": "space",
                "space_event": str(shot.get("primary_surface", "")).strip(),
                "continuity_lock": str(brief.get("identity_core", "")).strip(),
                "scene_change_level": "evolve",
                "anchor_strategy": "refine_anchor",
                "continuity_basis": "heroine",
                "edit_role": str(shot.get("story_function", "")).strip(),
                "camera_language": "",
                "pose_delta": str(shot.get("dominant_action", "")).strip(),
                "emotion": str(shot.get("continuity_delta", "")).strip(),
                "scene_detail": str(shot.get("primary_surface", "")).strip(),
                "motion_hint": str(shot.get("dominant_action", "")).strip(),
                "workflow_motion_clause": str(shot.get("dominant_action", "")).strip(),
                "space_relation": str(shot.get("world_zone", "")).strip(),
                "start_frame": {},
                "end_frame": {},
                "kinetic_transition": "carry",
                "lighting_fx": "",
                "kinetic_intensity": "medium",
                "location_family": str(shot.get("ref_archetype", "")).strip(),
                "composition_shape": "",
                "palette_mode": "",
                "character_render_mode": "cinematic heroine continuity",
                "face_exposure_level": "soft",
                "heroine_visibility": "clear",
                "continuity_priority": "high",
                "wardrobe_read": "high",
                "hero_frame_score": 2,
                "consistency_need": "high",
                "mv_function": str(shot.get("story_goal", "")).strip(),
                "return_weight": 2,
                "edit_density": "medium",
                "shot_priority": "support",
                "transition_role": "carry",
                "seed": idx,
                "retry": 0,
            }
        )
    return {
        "master_anchor": {
            "prompt_text": build_tti_anchor_master_prompt(config),
            "seed": 1,
            "kinetic_transition": "anchor",
        },
        "shots": tti_shots,
    }


def build_tti_anchor_master_prompt(config: dict) -> str:
    brief = build_director_brief_intent(config)
    hooks = ", ".join(brief.get("identity_hooks", []))
    wardrobe_guidance = str(brief.get("anchor_wardrobe_guidance", "")).strip()
    anchor_avoid = str(brief.get("anchor_avoid", "")).strip()
    grammar = tti_anchor_families()
    grammar_contract = " ".join(str(row.get("contract", "")).strip() for row in grammar if str(row.get("contract", "")).strip())
    identity_priority = ", ".join(
        str(item).strip()
        for row in grammar
        for item in row.get("identity_priority", [])
        if str(item).strip()
    )
    body_framing = " ".join(str(row.get("body_framing", "")).strip() for row in grammar if str(row.get("body_framing", "")).strip())
    background_policy = " ".join(str(row.get("background_policy", "")).strip() for row in grammar if str(row.get("background_policy", "")).strip())
    suppression = " ".join(str(row.get("suppression", "")).strip() for row in grammar if str(row.get("suppression", "")).strip())
    return " ".join(
        part
        for part in [
            f"{brief['style_contract']}.",
            f"{brief['identity_core']}.",
            f"Identity hooks: {hooks}." if hooks else "",
            "Create a production-ready master anchor for downstream reference matching.",
            grammar_contract,
            f"Identity priority: {identity_priority}." if identity_priority else "",
            body_framing,
            background_policy,
            "Wardrobe should read as polished everyday idol styling rather than a costume.",
            wardrobe_guidance,
            anchor_avoid,
            suppression,
            "High-end casting still, neutral continuity anchor, realistic skin detail, clean fabric response, and no dramatic scene action baked into the frame.",
        ]
        if str(part).strip()
    )
