from __future__ import annotations


def build_citypop_prompt_seed(concept_text: str, citypop_bible: dict, shot: dict) -> str:
    concept = _concept_seed_phrase(concept_text)
    continuity = _continuity_anchor(shot)
    subject = _still_subject_phrase(shot)
    location = _still_location_phrase(shot)
    palette = _still_palette_phrase(shot, citypop_bible)
    return ", ".join(
        part
        for part in [
            concept,
            continuity,
            subject,
            location,
            palette,
            "clean cel shading",
            "single coherent night-drive world",
            "stable character identity",
            "film grain",
        ]
        if part
    )


def build_citypop_prompt_draft(shot: dict) -> str:
    framing = _still_framing_phrase(shot)
    return ", ".join(
        part
        for part in [
            framing,
            "soft reflective portrait styling",
            "motion-safe keyframe",
            "no layered collage",
            "no abstract overlay",
            "film grain",
        ]
        if part
    )


def _concept_seed_phrase(concept_text: str) -> str:
    text = str(concept_text or "").strip()
    lower = text.lower()
    if "japanese" in lower and "city pop" in lower:
        return "Japanese 80s city pop music video"
    return text or "city pop music video"


def _continuity_anchor(shot: dict) -> str:
    role = str(shot.get("shot_role", "")).strip()
    section_name = str(shot.get("section_name", "")).strip().lower()
    if role.startswith("chorus"):
        return "same protagonist, same summer night-drive world, hook arrival in the same city"
    if role.startswith("verse"):
        return "same protagonist, same summer night-drive world, intimate movement through the city"
    if role.startswith("prechorus"):
        return "same protagonist, same summer night-drive world, anticipation tightens before the lift"
    if role.startswith("bridge"):
        return "same protagonist, same summer night-drive world, the night turns inward without changing worlds"
    if role.startswith("outro") or "outro" in section_name:
        return "same protagonist, same summer night-drive world, afterglow fading into the last lights"
    return "same protagonist, same summer night-drive world, continuity preserved"


def _still_subject_phrase(shot: dict) -> str:
    visual_mode = str(shot.get("visual_mode", "")).strip()
    if visual_mode == "profile_mood":
        return "young woman with long dark hair under fluorescent station light"
    if visual_mode == "night_drive":
        return "young woman driver with reflected night light and steady expression"
    if visual_mode == "window_reflection":
        return "young woman seen through side glass with reflected city lights"
    if visual_mode == "city_glance":
        return "young woman turning toward the camera through city reflections"
    if visual_mode == "chorus_performance":
        return "a close-up of a singer facing the camera with neon reflections and vivid expression"
    if visual_mode == "neon_release":
        return "young woman framed by neon reflections and moving city light"
    if visual_mode == "night_bridge":
        return "young woman with bridge lights behind her"
    if visual_mode == "memory_flash":
        return "young woman in a soft afterglow portrait with wind in her hair"
    if visual_mode == "bridge_transition":
        return "young woman shifting from reflection to open night air"
    return "young woman in a reflective summer night portrait"


def _still_location_phrase(shot: dict) -> str:
    visual_mode = str(shot.get("visual_mode", "")).strip()
    mapping = {
        "profile_mood": "night station interior with dark glass panels",
        "night_drive": "night expressway interior with passing street light and reflected city glow",
        "window_reflection": "car side window with layered reflections and city light spill",
        "city_glance": "night boulevard glass reflection with passing shop lights",
        "chorus_performance": "glowing city light reflections with a nightlife backdrop",
        "neon_release": "night boulevard light across wet street and polished surfaces",
        "night_bridge": "bridge lights in soft focus behind the subject",
        "memory_flash": "soft city skyline reflection at dusk",
        "bridge_transition": "transition between street light and reflective glass in the same city",
    }
    return mapping.get(visual_mode, "night city reflections")


def _still_palette_phrase(shot: dict, citypop_bible: dict) -> str:
    visual_mode = str(shot.get("visual_mode", "")).strip()
    if visual_mode in {"night_drive", "window_reflection", "night_bridge", "chorus_performance"}:
        return "deep blue and neon magenta palette"
    if visual_mode in {"memory_flash", "profile_mood"}:
        return "soft dusk violet and cool pink palette"
    if visual_mode in {"neon_release", "city_glance"}:
        return "deep blue and warm amber night palette"
    palette = [str(x).strip() for x in citypop_bible.get("palette", []) if str(x).strip()]
    return ", ".join(palette[:2])


def _still_framing_phrase(shot: dict) -> str:
    visual_mode = str(shot.get("visual_mode", "")).strip()
    mapping = {
        "profile_mood": "tight portrait close-up",
        "night_drive": "tight close-up with reflected night light",
        "window_reflection": "tight close-up through reflective glass",
        "city_glance": "three-quarter reflective close-up",
        "chorus_performance": "bold front-facing close-up",
        "neon_release": "medium close-up with neon framing",
        "night_bridge": "close-up with bridge lights in the background",
        "memory_flash": "soft portrait close-up",
        "bridge_transition": "clean reflective close-up",
    }
    return mapping.get(visual_mode, "clean cinematic close-up")
