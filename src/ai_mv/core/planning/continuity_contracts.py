from __future__ import annotations



def build_continuity_contract(shot: dict) -> dict:
    return {
        "protagonist_anchor": str(shot.get("protagonist_anchor", "")).strip(),
        "world_anchor": str(shot.get("world_anchor", "")).strip(),
        "wardrobe_anchor": _wardrobe_anchor(shot),
        "no_competing_subjects": True,
        "time_band_anchor": "same concept time and lighting band",
    }



def build_shot_relation_contract(shot: dict) -> dict:
    explicit = shot.get("shot_relation_contract") if isinstance(shot.get("shot_relation_contract"), dict) else {}
    if explicit:
        return {
            "relation_to_previous_shot": str(explicit.get("relation_to_previous_shot", "")).strip(),
            "camera_distance_progression": str(explicit.get("camera_distance_progression", "")).strip(),
            "same_block_vs_new_block": str(explicit.get("same_block_vs_new_block", "")).strip(),
            "emotional_delta": str(explicit.get("emotional_delta", "")).strip(),
        }
    section_type = str(shot.get("section_type", "")).strip().lower()
    framing_intent = str(shot.get("framing_intent", "")).strip()
    if section_type == "intro":
        return {
            "relation_to_previous_shot": "sequence opener",
            "camera_distance_progression": "set baseline distance",
            "same_block_vs_new_block": "same block baseline",
            "emotional_delta": "establish opening emotional baseline",
        }
    progression = {
        "establishing_wide": "hold or widen from previous shot",
        "hero_medium": "move closer than previous shot",
        "connective_medium": "shift laterally while keeping distance readable",
        "performance_medium": "move into performance distance",
        "release_wide": "step wider for release",
    }.get(framing_intent, "adjust distance without breaking continuity")
    emotional = {
        "chorus": "open into hook release without changing world",
        "bridge": "turn inward without changing world",
        "outro": "resolve into afterglow on the same block",
    }.get(section_type, "increase intimacy without changing world")
    return {
        "relation_to_previous_shot": "continue same protagonist and world from previous shot",
        "camera_distance_progression": progression,
        "same_block_vs_new_block": "same block, new angle",
        "emotional_delta": emotional,
    }



def _wardrobe_anchor(shot: dict) -> str:
    continuity = shot.get("continuity_contract") if isinstance(shot.get("continuity_contract"), dict) else {}
    explicit = str(continuity.get("wardrobe_anchor", "")).strip()
    if explicit:
        return explicit
    protagonist_anchor = str(shot.get("protagonist_anchor", "")).strip().lower()
    if "dark outerwear silhouette" in protagonist_anchor:
        return "stable dark outerwear silhouette"
    return "stable signature silhouette"
