from __future__ import annotations

from ai_mv.styles.citypop.rules import apply_citypop_section_variants, citypop_section_shot_specs



def synthwave_section_shot_specs(section_type: str, duration_sec: float) -> list[dict]:
    return citypop_section_shot_specs(section_type, duration_sec)



def apply_synthwave_section_variants(section_type: str, parts: list[dict]) -> list[dict]:
    return apply_citypop_section_variants(section_type, parts)
