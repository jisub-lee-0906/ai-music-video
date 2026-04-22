from __future__ import annotations


def alt_pop_section_shot_specs(section_type: str, duration_sec: float) -> list[dict]:
    render_mode = "ia2v"
    if section_type == "intro":
        return [_spec("intro_edge", "rooftop_edge", "low", render_mode, 1.0)]
    if section_type == "chorus":
        return [_spec("chorus_front", "chorus_front", "high", render_mode, 1.0)]
    if section_type == "pre_chorus":
        return [_spec("pre_chorus_tension", "pre_chorus_tension", "medium", render_mode, 1.0)]
    if section_type == "bridge":
        return [_spec("bridge_glass", "bridge_glass", "medium", render_mode, 1.0)]
    if section_type == "outro":
        return [_spec("outro_release", "release_stride", "low", render_mode, 1.0)]
    return [_spec("verse_edge", "glass_corridor", "medium", render_mode, 1.0)]



def apply_alt_pop_section_variants(section_type: str, parts: list[dict]) -> list[dict]:
    return [dict(part) for part in parts]



def _spec(shot_role: str, visual_mode: str, energy: str, render_mode: str, weight: float) -> dict:
    return {
        "shot_role": shot_role,
        "visual_mode": visual_mode,
        "energy": energy,
        "render_mode": render_mode,
        "weight": weight,
    }
