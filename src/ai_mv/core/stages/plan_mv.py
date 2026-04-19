from __future__ import annotations

from ai_mv.core.contracts.stage_io import StageInput, StageOutput
from ai_mv.core.planning.creative_direction import build_creative_direction
from ai_mv.core.planning.render_items import build_render_item
from ai_mv.core.planning.sections import normalized_sections
from ai_mv.core.planning.shot_plan import build_shot_plan
from ai_mv.styles.resolver import get_style_bible, resolve_style_name



def run_plan_mv(stage_input: StageInput) -> StageOutput:
    payload = build_plan_preview_payload(stage_input.config, stage_input.payload)
    return StageOutput("plan_mv", "done", payload, [])



def build_plan_preview_payload(config: dict, payload: dict) -> dict:
    concept_text = str(payload.get("concept_text") or config.get("concept_text", "")).strip()
    audio_map = dict(payload.get("audio_map", {}))
    duration = float(audio_map.get("duration_sec", 16.0) or 16.0)
    planning = config.get("planning", {}) if isinstance(config, dict) else {}
    default_style_name = str(planning.get("default_style_name", "")).strip() or None
    style_name = resolve_style_name(concept_text, default_style_name=default_style_name)
    style_bible = get_style_bible(style_name)
    sections = normalized_sections(audio_map, duration)
    creative_direction = build_creative_direction(concept_text=concept_text, style_name=style_name, sections=sections)
    shot_plan = build_shot_plan(config, sections, style_name=style_name)
    render_plan = [build_render_item(config, concept_text, style_name, style_bible, shot) for shot in shot_plan]
    return {
        "style_name": style_name,
        "style_bible": style_bible,
        "creative_direction": creative_direction,
        "shot_plan": shot_plan,
        "render_plan": render_plan,
        "workflow_inputs": {
            **dict(payload.get("workflow_inputs", {})),
            "plan": {
                "shot_count": len(shot_plan),
                "concept_text": concept_text,
                "style_name": style_name,
                "section_count": len(sections),
                "music_section_count": len(sections),
            },
        },
    }
