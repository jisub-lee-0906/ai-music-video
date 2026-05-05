from __future__ import annotations


def idol_pop_section_shot_specs(section_type: str, duration_sec: float) -> list[dict]:
    render_mode = "ia2v"
    if section_type == "intro":
        return [_spec("intro_glow", "boulevard_intro_glow", "medium", render_mode, 1.0)]
    if section_type == "chorus":
        return [_spec("chorus_front", "chorus_front_lights", "high", render_mode, 1.0)]
    if section_type == "pre_chorus":
        return [_spec("pre_chorus_lift", "pre_chorus_lift", "high", render_mode, 1.0)]
    if section_type == "bridge":
        return [_spec("bridge_close", "bridge_close_gloss", "medium", render_mode, 1.0)]
    if section_type == "outro":
        return [_spec("source_bound_release", "source_bound_release_stride", "medium", render_mode, 1.0)]
    return [_spec("verse_confidence", "source_bound_pop_walk", "medium", render_mode, 1.0)]


def apply_idol_pop_section_variants(section_type: str, parts: list[dict]) -> list[dict]:
    return [dict(part) for part in parts]


def _spec(shot_role: str, visual_mode: str, energy: str, render_mode: str, weight: float) -> dict:
    return {
        "shot_role": shot_role,
        "visual_mode": visual_mode,
        "energy": energy,
        "render_mode": render_mode,
        "weight": weight,
    }
