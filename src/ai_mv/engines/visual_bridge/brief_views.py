from __future__ import annotations


def build_world_bible(brief: dict) -> dict:
    return {
        "hero_identity": str(brief.get("hero_identity", "")).strip(),
        "world_rules": str(brief.get("world_rules", "")).strip(),
        "visual_motifs": [str(x).strip() for x in brief.get("visual_motifs", []) if str(x).strip()],
        "negative_constraints": [str(x).strip() for x in brief.get("negative_constraints", []) if str(x).strip()],
    }


def build_section_dramaturgy(brief: dict) -> list[dict]:
    out: list[dict] = []
    for row in brief.get("section_briefs", []):
        out.append(
            {
                "section_name": str(row.get("section_name", "")).strip(),
                "emotional_arc": str(row.get("emotional_arc", "")).strip(),
                "story_beat": str(row.get("story_beat", "")).strip(),
                "location_anchor": str(row.get("location_anchor", "")).strip(),
                "palette_hint": str(row.get("palette_hint", "")).strip(),
                "lighting_hint": str(row.get("lighting_hint", "")).strip(),
                "staging_hint": str(row.get("staging_hint", "")).strip(),
            }
        )
    return out


def world_bible(brief: dict) -> dict:
    data = brief.get("world_bible", {}) if isinstance(brief, dict) else {}
    if isinstance(data, dict) and data:
        return build_world_bible(data)
    return build_world_bible(brief)


def section_dramaturgy(brief: dict) -> list[dict]:
    data = brief.get("section_dramaturgy", []) if isinstance(brief, dict) else []
    if isinstance(data, list) and data:
        return build_section_dramaturgy({"section_briefs": data})
    return build_section_dramaturgy(brief)
