from __future__ import annotations

from ai_mv.styles.citypop.bible import get_citypop_bible
from ai_mv.styles.citypop.prompting import build_citypop_prompt_draft, build_citypop_prompt_seed
from ai_mv.styles.citypop.rules import apply_citypop_section_variants, citypop_section_shot_specs
from ai_mv.styles.synthwave.bible import get_synthwave_bible
from ai_mv.styles.synthwave.prompting import build_synthwave_prompt_draft, build_synthwave_prompt_seed
from ai_mv.styles.synthwave.rules import apply_synthwave_section_variants, synthwave_section_shot_specs



def resolve_style_name(concept_text: str) -> str:
    text = str(concept_text or "").strip().lower()
    if "synthwave" in text:
        return "synthwave"
    return "citypop"



def get_style_bible(style_name: str) -> dict:
    if style_name == "synthwave":
        return get_synthwave_bible()
    return get_citypop_bible()



def build_style_prompt_seed(style_name: str, concept_text: str, style_bible: dict, shot: dict) -> str:
    if style_name == "synthwave":
        return build_synthwave_prompt_seed(concept_text, style_bible, shot)
    return build_citypop_prompt_seed(concept_text, style_bible, shot)



def build_style_prompt_draft(style_name: str, shot: dict) -> str:
    if style_name == "synthwave":
        return build_synthwave_prompt_draft(shot)
    return build_citypop_prompt_draft(shot)



def style_section_shot_specs(style_name: str, section_type: str, duration_sec: float) -> list[dict]:
    if style_name == "synthwave":
        return synthwave_section_shot_specs(section_type, duration_sec)
    return citypop_section_shot_specs(section_type, duration_sec)



def apply_style_section_variants(style_name: str, section_type: str, parts: list[dict]) -> list[dict]:
    if style_name == "synthwave":
        return apply_synthwave_section_variants(section_type, parts)
    return apply_citypop_section_variants(section_type, parts)
