from __future__ import annotations

from ai_mv.core.contracts.stage_io import StageInput, StageOutput
from ai_mv.core.planning.creative_direction import build_creative_direction
from ai_mv.core.planning.render_items import build_render_item
from ai_mv.core.planning.sections import normalized_sections
from ai_mv.core.planning.shot_plan import build_shot_plan
from ai_mv.styles.resolver import get_style_bible, resolve_style_selection



def run_plan_mv(stage_input: StageInput) -> StageOutput:
    payload = build_plan_preview_payload(stage_input.config, stage_input.payload)
    return StageOutput("plan_mv", "done", payload, [])



def build_plan_preview_payload(config: dict, payload: dict) -> dict:
    concept_text = str(payload.get("concept_text") or config.get("concept_text", "")).strip()
    audio_map = dict(payload.get("audio_map", {}))
    duration = float(audio_map.get("duration_sec", 16.0) or 16.0)
    planning = config.get("planning", {}) if isinstance(config, dict) else {}
    default_style_name = str(planning.get("default_style_name", "")).strip() or None
    continuity_mode = str(planning.get("continuity_mode", "strict")).strip() or "strict"
    style_resolution = resolve_style_selection(concept_text, default_style_name=default_style_name)
    style_lane = style_resolution["style_lane"]
    style_bible = get_style_bible(style_lane)
    sections = normalized_sections(audio_map, duration)
    creative_direction = build_creative_direction(
        concept_text=concept_text,
        style_name=style_lane,
        sections=sections,
        continuity_mode=continuity_mode,
    )
    shot_plan = build_shot_plan(config, sections, style_name=style_lane)
    _thread_continuity_anchor_bundle(shot_plan, creative_direction)
    _thread_shot_relation_contracts(shot_plan)
    material_plan = build_material_plan(style_lane, shot_plan)
    render_plan = [build_render_item(config, concept_text, style_lane, style_bible, shot) for shot in shot_plan]
    return {
        "style_lane": style_lane,
        "style_resolution": style_resolution,
        "style_bible": style_bible,
        "creative_direction": creative_direction,
        "section_plan": sections,
        "shot_plan": shot_plan,
        "material_plan": material_plan,
        "render_plan": render_plan,
        "workflow_inputs": {
            **dict(payload.get("workflow_inputs", {})),
            "plan": {
                "shot_count": len(shot_plan),
                "material_count": len(material_plan),
                "concept_text": concept_text,
                "style_lane": style_lane,
                "section_count": len(sections),
                "music_section_count": len(sections),
            },
        },
    }


def build_material_plan(style_name: str, shot_plan: list[dict]) -> list[dict]:
    material_plan: list[dict] = []
    for idx, shot in enumerate(shot_plan, start=1):
        role = _material_role_for_shot(shot)
        material_plan.append(
            {
                "material_id": f"MAT_{idx:03d}",
                "section_id": str(shot.get("section_id", "")).strip(),
                "role": role,
                "style_lane": style_name,
                "mode_hint": _mode_hint_for_shot(shot),
                "shot_intent": str(shot.get("shot_role", "")).strip(),
                "target_aspect": "1280x720",
                "needs_front_readability": role == "performance_source",
                "continuity_constraints": {
                    "same_subject": True,
                    "same_world": True,
                    "same_time_band": True,
                },
            }
        )
        shot["material_id"] = material_plan[-1]["material_id"]
    return material_plan


def _material_role_for_shot(shot: dict) -> str:
    workflow_intent = str(shot.get("workflow_intent", "")).strip()
    section_type = str(shot.get("section_type", "")).strip()
    if workflow_intent == "audio_reactive_candidate" or section_type == "chorus":
        return "performance_source"
    if workflow_intent == "bridge_candidate" or section_type == "bridge":
        return "bridge_target"
    if section_type == "intro":
        return "anchor_source"
    return "general_source"


def _mode_hint_for_shot(shot: dict) -> str:
    workflow_intent = str(shot.get("workflow_intent", "")).strip()
    section_type = str(shot.get("section_type", "")).strip()
    if workflow_intent == "audio_reactive_candidate" or section_type == "chorus":
        return "performance"
    if workflow_intent == "bridge_candidate" or section_type == "bridge":
        return "bridge_transition"
    if section_type == "intro":
        return "anchor"
    return "general_narrative"


def _thread_continuity_anchor_bundle(shot_plan: list[dict], creative_direction: dict) -> None:
    protagonist_anchor = str(creative_direction.get("protagonist_anchor", "")).strip() if isinstance(creative_direction, dict) else ""
    world_anchor = str(creative_direction.get("world_anchor", "")).strip() if isinstance(creative_direction, dict) else ""
    for shot in shot_plan:
        if not isinstance(shot, dict):
            continue
        if protagonist_anchor:
            shot["protagonist_anchor"] = protagonist_anchor
        if world_anchor:
            shot["world_anchor"] = world_anchor
        shot["continuity_contract"] = {
            "protagonist_anchor": protagonist_anchor,
            "world_anchor": world_anchor,
            "wardrobe_anchor": "stable dark outerwear silhouette",
            "no_competing_subjects": True,
            "time_band_anchor": "same night time band",
        }



def _thread_shot_relation_contracts(shot_plan: list[dict]) -> None:
    previous_shot: dict | None = None
    for shot in shot_plan:
        if not isinstance(shot, dict):
            continue
        if previous_shot is None:
            shot["shot_relation_contract"] = {
                "relation_to_previous_shot": "sequence opener",
                "camera_distance_progression": "set baseline distance",
                "same_block_vs_new_block": "same block baseline",
                "emotional_delta": "establish lonely night-world baseline",
            }
        else:
            shot["shot_relation_contract"] = {
                "relation_to_previous_shot": "continue same protagonist and world from previous shot",
                "camera_distance_progression": _camera_distance_progression(shot),
                "same_block_vs_new_block": _same_block_vs_new_block(shot, previous_shot),
                "emotional_delta": _emotional_delta(shot),
            }
        previous_shot = shot



def _camera_distance_progression(shot: dict) -> str:
    framing_intent = str(shot.get("framing_intent", "")).strip()
    return {
        "establishing_wide": "hold or widen from previous shot",
        "hero_medium": "move closer than previous shot",
        "connective_medium": "shift laterally while keeping distance readable",
        "performance_medium": "move into performance distance",
        "release_wide": "step wider for release",
    }.get(framing_intent, "adjust distance without breaking continuity")



def _same_block_vs_new_block(current_shot: dict, previous_shot: dict) -> str:
    current_section = str(current_shot.get("section_type", "")).strip()
    previous_section = str(previous_shot.get("section_type", "")).strip()
    if current_section == previous_section:
        return "same block, new angle"
    return "same block, evolved staging"



def _emotional_delta(shot: dict) -> str:
    section_type = str(shot.get("section_type", "")).strip().lower()
    return {
        "chorus": "open into hook release without changing world",
        "bridge": "turn inward without changing world",
        "outro": "resolve into afterglow on the same block",
    }.get(section_type, "increase intimacy without changing world")
