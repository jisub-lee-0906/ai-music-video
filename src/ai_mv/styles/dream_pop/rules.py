from __future__ import annotations


def dream_pop_section_shot_specs(section_type: str, duration_sec: float) -> list[dict]:
    render_mode = "i2v"
    if section_type == "intro":
        return [_spec("intro_haze", "moonlit_overpass", "low", render_mode, 1.0)]
    if section_type == "chorus":
        return [_spec("chorus_bloom", "chorus_bloom", "high", render_mode, 1.0)]
    if section_type == "pre_chorus":
        return [_spec("pre_chorus_lift", "pre_chorus_lift", "medium", render_mode, 1.0)]
    if section_type == "bridge":
        return [_spec("bridge_hush", "bridge_hush", "medium", render_mode, 1.0)]
    if section_type == "outro":
        return [_spec("outro_afterglow", "afterglow_walk", "low", render_mode, 1.0)]
    return [_spec("verse_drift", "window_haze", "medium", render_mode, 1.0)]



def apply_dream_pop_section_variants(section_type: str, parts: list[dict]) -> list[dict]:
    return [dict(part) for part in parts]



def _spec(shot_role: str, visual_mode: str, energy: str, render_mode: str, weight: float) -> dict:
    return {
        "shot_role": shot_role,
        "visual_mode": visual_mode,
        "energy": energy,
        "render_mode": render_mode,
        "weight": weight,
    }
