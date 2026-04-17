from __future__ import annotations


def synthwave_section_shot_specs(section_type: str, duration_sec: float) -> list[dict]:
    render_mode = "i2v"
    if section_type == "intro":
        return [_spec("intro_glide", "laser_horizon", "low", render_mode, 1.0)]
    if section_type == "outro":
        return [_spec("outro_fade", "afterglow_escape", "low", render_mode, 1.0)]
    if section_type == "chorus":
        if duration_sec >= 7.0:
            return [
                _spec("chorus_breakout", "grid_surge", "high", render_mode, 0.5),
                _spec("chorus_cruise", "neon_run", "high", render_mode, 0.5),
            ]
        return [_spec("chorus_breakout", "grid_surge", "high", render_mode, 1.0)]
    if section_type == "bridge":
        return [_spec("bridge_descent", "tunnel_reveal", "medium", render_mode, 1.0)]
    if section_type == "pre_chorus":
        return [_spec("prechorus_charge", "dashboard_pulse", "medium", render_mode, 1.0)]
    if duration_sec >= 7.0:
        return [
            _spec("verse_cruise", "neon_highway", "medium", render_mode, 0.5),
            _spec("verse_reflection", "mirror_glass", "medium", render_mode, 0.5),
        ]
    return [_spec("verse_cruise", "neon_highway", "medium", render_mode, 1.0)]


def apply_synthwave_section_variants(section_type: str, parts: list[dict]) -> list[dict]:
    if not parts:
        return []
    out: list[dict] = []
    split_count = len(parts)
    for idx, part in enumerate(parts):
        role, visual = _shot_variant(section_type, idx, split_count, str(part.get("shot_role", "")), str(part.get("visual_mode", "")))
        out.append({**part, "shot_role": role, "visual_mode": visual})
    return out


def _shot_variant(section_type: str, idx: int, split_count: int, shot_role: str, visual_mode: str) -> tuple[str, str]:
    sequences = {
        "intro": [("intro_glide", "laser_horizon"), ("intro_approach", "neon_highway")],
        "verse": [("verse_cruise", "neon_highway"), ("verse_reflection", "mirror_glass"), ("verse_swerve", "dashboard_pulse"), ("verse_afterimage", "laser_horizon")],
        "pre_chorus": [("prechorus_charge", "dashboard_pulse"), ("prechorus_release", "mirror_glass")],
        "chorus": [("chorus_breakout", "grid_surge"), ("chorus_cruise", "neon_run"), ("chorus_lift", "skyline_bloom"), ("chorus_afterburn", "neon_run")],
        "bridge": [("bridge_descent", "tunnel_reveal"), ("bridge_escape", "afterglow_escape")],
        "outro": [("outro_fade", "afterglow_escape"), ("outro_tail", "skyline_bloom")],
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
