from __future__ import annotations

import zlib



def build_render_seed_for_shot(shot: dict) -> int:
    text = "|".join(
        [
            str(shot.get("shot_id", "")).strip(),
            str(shot.get("start_sec", "")).strip(),
            str(shot.get("duration_sec", "")).strip(),
            str(shot.get("visual_mode", "")).strip(),
            str(shot.get("render_mode", "")).strip(),
        ]
    ).encode("utf-8")
    return 1000 + int(zlib.crc32(text) % 1_000_000)



def build_variation_seed_for_shot(shot: dict) -> int:
    text = "|".join(
        [
            str(shot.get("shot_id", "")).strip(),
            str(shot.get("section_type", "")).strip(),
            str(shot.get("section_name", "")).strip(),
            str(shot.get("shot_role", "")).strip(),
            str(shot.get("visual_mode", "")).strip(),
            str(shot.get("start_sec", "")).strip(),
        ]
    ).encode("utf-8")
    return 2000 + int(zlib.crc32(text) % 1_000_000)



def build_variation_profile(variation_seed: int, shot: dict) -> dict:
    section_type = str(shot.get("section_type", "")).strip().lower()
    energy = str(shot.get("energy", "")).strip().lower()
    shot_role = str(shot.get("shot_role", "")).strip().lower()
    visual_mode = str(shot.get("visual_mode", "")).strip().lower()
    is_performance_peak = section_type == "chorus" or "chorus" in shot_role or "performance" in visual_mode
    framing_options = ["balanced", "subject_forward"] if is_performance_peak else ["balanced", "subject_forward", "environment_forward"]
    continuity_options = ["strict", "anchored"] if is_performance_peak else ["strict", "anchored", "expressive"]
    return {
        "variation_family": _pick_variant(variation_seed, ["editorial-a", "editorial-b", "editorial-c"]),
        "framing_variant": _pick_variant(variation_seed + 11, framing_options),
        "environment_variant": _pick_variant(variation_seed + 23, ["atmospheric", "textural", "spatial"]),
        "motion_variant": _pick_variant(variation_seed + 37, ["restrained", "gliding", "pulsed"]),
        "continuity_variant": _pick_variant(variation_seed + 53, continuity_options),
        "section_emphasis_variant": _section_emphasis_variant(section_type, energy, variation_seed + 71),
    }



def _pick_variant(seed: int, options: list[str]) -> str:
    if not options:
        return ""
    return options[int(seed) % len(options)]



def _section_emphasis_variant(section_type: str, energy: str, seed: int) -> str:
    normalized_type = str(section_type or "").strip()
    normalized_energy = str(energy or "").strip()
    if normalized_type == "chorus":
        return _pick_variant(seed, ["hook_forward", "lifted_release", "performance_peak"])
    if normalized_type == "bridge":
        return _pick_variant(seed, ["contrastive_turn", "late-night drift", "reset_suspension"])
    if normalized_type in {"intro", "outro"}:
        return _pick_variant(seed, ["world_anchor", "afterglow_hold", "slow_release"])
    if normalized_energy == "high":
        return _pick_variant(seed, ["forward_drive", "cinematic_push", "contained_intensity"])
    return _pick_variant(seed, ["sequence_support", "observational_flow", "ambient_progression"])
