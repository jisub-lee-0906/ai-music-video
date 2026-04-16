from __future__ import annotations


def build_synthwave_prompt_seed(concept_text: str, style_bible: dict, shot: dict) -> str:
    text = str(concept_text or "").strip()
    concept = "retro synthwave music video" if "synthwave" in text.lower() else (text or "retro synthwave music video")
    palette = ", ".join(str(x).strip() for x in style_bible.get("palette", [])[:2] if str(x).strip())
    visual_mode = str(shot.get("visual_mode", "")).strip()
    scene = {
        "night_drive": "neon highway glide under sodium and magenta light",
        "window_reflection": "chrome reflections folding across glass and dashboard light",
        "chorus_performance": "hero performance framed by a glowing skyline and wet asphalt",
        "city_glance": "side glance toward neon signs and passing light trails",
        "memory_flash": "soft retro memory bloom with VHS glow and dusk fog",
        "night_bridge": "suspended overpass crossing above electric city light",
        "profile_mood": "solo portrait under electric violet station light",
        "bridge_transition": "transition between cockpit glow and open neon boulevard",
        "neon_release": "wide release into a glowing retro skyline",
    }.get(visual_mode, "retro synthwave visual beat")
    return ", ".join(
        part
        for part in [
            concept,
            f"scene event: {scene}",
            palette,
            "retro synthwave illustration",
            "neon glow",
            "analog atmosphere",
        ]
        if part
    )



def build_synthwave_prompt_draft(shot: dict) -> str:
    visual_mode = str(shot.get("visual_mode", "")).strip()
    framing = {
        "profile_mood": "tight electric portrait",
        "night_drive": "windshield close-up with reflected light trails",
        "window_reflection": "chrome reflection close-up",
        "city_glance": "three-quarter neon close-up",
        "chorus_performance": "front-facing skyline performance close-up",
        "neon_release": "wide boulevard release framing",
        "night_bridge": "overpass silhouette close-up",
        "memory_flash": "soft VHS portrait framing",
        "bridge_transition": "retro transition close-up",
    }.get(visual_mode, "retro synthwave close-up")
    return ", ".join(
        [
            framing,
            "retro synthwave illustration",
            "neon glow",
            "analog atmosphere",
        ]
    )
