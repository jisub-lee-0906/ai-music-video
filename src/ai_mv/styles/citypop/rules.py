from __future__ import annotations


def citypop_section_shot_specs(section_type: str, duration_sec: float) -> list[dict]:
    m1_mode = "i2v"
    if section_type == "intro":
        return [_spec("intro_mood", "empty_boulevard_anchor", "low", m1_mode, 1.0)]
    if section_type == "outro":
        return [_spec("outro_release", "skyline_release", "low", m1_mode, 1.0)]
    if section_type == "chorus":
        if duration_sec >= 7.0:
            return [
                _spec("chorus_arrive", "chorus_performance", "high", m1_mode, 0.5),
                _spec("chorus_hold", "neon_release", "high", m1_mode, 0.5),
            ]
        return [_spec("chorus_peak", "chorus_performance", "high", m1_mode, 1.0)]
    if section_type == "bridge":
        return [_spec("bridge_shift", "bridge_overlook", "medium", m1_mode, 1.0)]
    if section_type == "pre_chorus":
        return [_spec("prechorus_lift", "partial_figure_transition", "medium", m1_mode, 1.0)]
    if duration_sec >= 7.0:
        return [
            _spec("verse_setup", "night_drive", "medium", m1_mode, 0.5),
            _spec("verse_detail", "window_reflection", "medium", m1_mode, 0.5),
        ]
    return [_spec("verse_flow", "night_drive", "medium", m1_mode, 1.0)]



def apply_citypop_section_variants(section_type: str, parts: list[dict]) -> list[dict]:
    if not parts:
        return []
    out: list[dict] = []
    split_count = len(parts)
    for idx, part in enumerate(parts):
        role, visual = _shot_variant(section_type, idx, split_count, str(part.get("shot_role", "")), str(part.get("visual_mode", "")))
        out.append(
            {
                **part,
                "shot_role": role,
                "visual_mode": visual,
            }
        )
    return out



def _shot_variant(section_type: str, idx: int, split_count: int, shot_role: str, visual_mode: str) -> tuple[str, str]:
    sequences = {
        "intro": [("intro_mood", "empty_boulevard_anchor"), ("intro_drive", "night_drive")],
        "verse": [("verse_setup", "night_drive"), ("verse_detail", "rain_window_detail"), ("verse_flow", "night_drive"), ("verse_glow", "city_glance")],
        "pre_chorus": [("prechorus_lift", "partial_figure_transition"), ("prechorus_tension", "rain_window_detail")],
        "chorus": [("chorus_arrive", "chorus_performance"), ("chorus_hold", "neon_release"), ("chorus_sweep", "chorus_performance"), ("chorus_afterglow", "neon_release")],
        "bridge": [("bridge_shift", "bridge_overlook"), ("bridge_drift", "rain_window_detail")],
        "outro": [("outro_release", "skyline_release"), ("outro_tail", "skyline_release")],
    }
    options = sequences.get(section_type, [(shot_role, visual_mode)])
    role, visual = options[min(idx, len(options) - 1)]
    if split_count <= len(options):
        return role, visual
    return (f"{role}_{idx + 1}", visual)



def _spec(shot_role: str, visual_mode: str, energy: str, render_mode: str, weight: float) -> dict:
    return {
        "shot_role": shot_role,
        "visual_mode": visual_mode,
        "energy": energy,
        "render_mode": render_mode,
        "weight": weight,
    }
