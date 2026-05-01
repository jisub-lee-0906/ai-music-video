from __future__ import annotations

from ai_mv.styles.resolver import resolve_style_name



def resolve_render_item_inputs(
    config: dict,
    concept_text: str,
    style_name_or_bible,
    style_bible_or_shot,
    shot: dict | None = None,
) -> dict:
    if shot is None:
        planning = config.get("planning", {}) if isinstance(config, dict) else {}
        default_style_name = str(planning.get("default_style_name", "")).strip() or None
        style_name = resolve_style_name(concept_text, default_style_name=default_style_name)
        style_bible = style_name_or_bible
        resolved_shot = style_bible_or_shot
    else:
        style_name = str(style_name_or_bible)
        style_bible = style_bible_or_shot
        resolved_shot = shot
    return {"style_name": style_name, "style_bible": style_bible, "shot": resolved_shot}
