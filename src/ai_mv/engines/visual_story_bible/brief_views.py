from __future__ import annotations

def build_story_world(brief: dict) -> dict:
    return {
        "hero_identity": str(brief.get("hero_identity_lock", "")).strip(),
        "heroine_invariants": str(brief.get("heroine_invariants", brief.get("hero_identity_lock", ""))).strip(),
        "world_rules": str(brief.get("world_rules", "")).strip(),
        "world_invariants": str(brief.get("world_invariants", brief.get("world_rules", ""))).strip(),
        "recurring_location_families": [str(x).strip() for x in brief.get("recurring_location_families", []) if str(x).strip()],
        "forbidden_drift": [str(x).strip() for x in brief.get("forbidden_drift", []) if str(x).strip()],
    }


def build_beat_atoms(brief: dict) -> list[dict]:
    out: list[dict] = []
    for row in brief.get("lyric_beats", []):
        out.append(
            {
                "section_name": str(row.get("section_name", "")).strip(),
                "emotional_arc": str(row.get("emotional_turn", "")).strip(),
                "story_beat": str(row.get("visible_action", "")).strip(),
                "location_anchor": str(row.get("location_family", "")).strip(),
                "palette_hint": str(row.get("palette_hint", "")).strip(),
                "lighting_hint": str(row.get("lighting_hint", "")).strip(),
                "staging_hint": str(row.get("camera_commitment", "")).strip(),
                "composition_shape": str(row.get("composition_shape", "")).strip(),
                "palette_mode": str(row.get("palette_mode", "")).strip(),
                "character_render_mode": str(row.get("character_render_mode", "")).strip(),
                "escalation_level": str(row.get("payoff_role", "")).strip(),
                "motion_axis": str(row.get("continuity_anchor", "")).strip(),
                "lyric_beat_id": str(row.get("beat_id", "")).strip(),
            }
        )
    return out


def compact_world_atoms(brief: dict) -> dict:
    world = build_story_world(brief)
    return {
        "hero_identity": _compact_hero_identity(world.get("heroine_invariants", "") or world.get("hero_identity", "")),
        "heroine_invariants": str(world.get("heroine_invariants", "") or world.get("hero_identity", "")).strip(),
        "world_rules": str(world.get("world_rules", "")).strip(),
        "world_invariants": str(world.get("world_invariants", "") or world.get("world_rules", "")).strip(),
        "visual_style_contract": _compact_style_contract(brief.get("visual_style_contract", "")),
    }


def compact_section_atoms(brief: dict, section_name: str, lyric_beat_id: str = "") -> dict:
    target = str(section_name).strip()
    rows = build_beat_atoms(brief)
    beat_target = str(lyric_beat_id).strip()
    if beat_target:
        for row in rows:
            if str(row.get("lyric_beat_id", "")).strip() == beat_target:
                return {
                    "section_name": target,
                    "story_beat": str(row.get("story_beat", "")).strip(),
                    "location_anchor": str(row.get("location_anchor", "")).strip(),
                    "staging_hint": str(row.get("staging_hint", "")).strip(),
                    "lighting_hint": str(row.get("lighting_hint", "")).strip(),
                    "palette_hint": str(row.get("palette_hint", "")).strip(),
                    "composition_shape": str(row.get("composition_shape", "")).strip(),
                    "palette_mode": str(row.get("palette_mode", "")).strip(),
                    "character_render_mode": str(row.get("character_render_mode", "")).strip(),
                    "emotional_arc": str(row.get("emotional_arc", "")).strip(),
                    "escalation_level": str(row.get("escalation_level", "")).strip(),
                    "motion_axis": str(row.get("motion_axis", "")).strip(),
                    "lyric_beat_id": str(row.get("lyric_beat_id", "")).strip(),
                }
    for row in rows:
        if str(row.get("section_name", "")).strip() == target:
            return {
                "section_name": target,
                "story_beat": str(row.get("story_beat", "")).strip(),
                "location_anchor": str(row.get("location_anchor", "")).strip(),
                "staging_hint": str(row.get("staging_hint", "")).strip(),
                "lighting_hint": str(row.get("lighting_hint", "")).strip(),
                "palette_hint": str(row.get("palette_hint", "")).strip(),
                "composition_shape": str(row.get("composition_shape", "")).strip(),
                "palette_mode": str(row.get("palette_mode", "")).strip(),
                "character_render_mode": str(row.get("character_render_mode", "")).strip(),
                "emotional_arc": str(row.get("emotional_arc", "")).strip(),
                "escalation_level": str(row.get("escalation_level", "")).strip(),
                "motion_axis": str(row.get("motion_axis", "")).strip(),
                "lyric_beat_id": str(row.get("lyric_beat_id", "")).strip(),
            }
    return {
        "section_name": target,
        "story_beat": "",
        "location_anchor": "",
        "staging_hint": "",
        "lighting_hint": "",
        "palette_hint": "",
        "composition_shape": "",
        "palette_mode": "",
        "character_render_mode": "",
        "emotional_arc": "",
        "escalation_level": "",
        "motion_axis": "",
        "lyric_beat_id": "",
    }


def _compact_hero_identity(text: object) -> str:
    return " ".join(str(text).strip().split())


def _compact_style_contract(text: object) -> str:
    return " ".join(str(text).strip().split())
