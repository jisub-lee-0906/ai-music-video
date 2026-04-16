from __future__ import annotations


def build_citypop_prompt_seed(concept_text: str, citypop_bible: dict, shot: dict) -> str:
    concept = _concept_seed_phrase(concept_text)
    progression = _section_progression_hint(shot)
    scene_event = _shot_scene_detail(shot)
    subject = _qwen_subject_phrase(shot)
    location = _qwen_location_phrase(shot)
    palette = _qwen_palette_phrase(shot, citypop_bible)
    return ", ".join(
        part
        for part in [
            concept,
            f"progression: {progression}" if progression else "",
            f"scene event: {scene_event}" if scene_event else "",
            subject,
            location,
            palette,
            "clean cel shading",
            "bold graphic composition",
            "80s japanese city pop illustration",
            "film grain",
        ]
        if part
    )



def build_citypop_prompt_draft(shot: dict) -> str:
    styling = _qwen_styling_phrase(shot)
    framing = _qwen_framing_phrase(shot)
    return ", ".join(
        part
        for part in [
            styling,
            framing,
            "clean cel shading",
            "bold graphic composition",
            "80s japanese city pop illustration",
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



def _section_progression_hint(shot: dict) -> str:
    name = str(shot.get("section_name", "")).strip().lower()
    if "pre-chorus 2" in name or "pre_chorus 2" in name:
        return "tension rises faster, less hesitation"
    if "pre-chorus" in name or "pre_chorus" in name:
        return "anticipation tightens before the lift"
    if "final chorus" in name:
        return "last release before dawn, emotionally resolved"
    if "chorus 2" in name:
        return "hook returns brighter, more exposed"
    if "chorus" in name:
        return "first payoff, arrival of the hook"
    if "verse 2" in name:
        return "same night, changed perspective"
    if "bridge" in name:
        return "the night turns inward before the final return"
    if "outro" in name:
        return "afterglow and tail lights fading out"
    return "opening pass through the night"



def _shot_scene_detail(shot: dict) -> str:
    visual_mode = str(shot.get("visual_mode", "")).strip()
    role = str(shot.get("shot_role", "")).strip()
    mapping = {
        "profile_mood": "solo lead portrait in a quiet city setting at blue hour with ambient glow on the face",
        "night_drive": "late-night city movement with reflected streetlights sliding across glass and metal surfaces",
        "window_reflection": "close-up with layered reflections across glass, cheek, or polished surfaces",
        "city_glance": "three-quarter glance toward passing signs, platform lights, or side streets",
        "chorus_performance": "intimate performance shot with the city opening behind the singer",
        "neon_release": "wide exterior pass through a lit boulevard or open night street",
        "night_bridge": "quiet transitional night crossing with sparse traffic and open dark space below",
        "memory_flash": "soft memory flash with film-grain warmth and moving air in the frame",
        "bridge_transition": "visual handoff from interior reflection to the next scene anchor",
    }
    detail = mapping.get(visual_mode, "city pop shot with one clear visual beat")
    if role.startswith("verse_detail"):
        return "close-up on hands, glass, fabric, and reflected city light in a quiet intimate moment"
    if role.startswith("chorus_hold"):
        return "held emotional release as the hook settles in and the city lights stretch behind the subject"
    if role.startswith("chorus_arrive"):
        return "the hook lands as the camera meets the singer head-on"
    if role.startswith("outro_tail"):
        return "the last light drifting away after the song resolves"
    return detail



def _qwen_subject_phrase(shot: dict) -> str:
    visual_mode = str(shot.get("visual_mode", "")).strip()
    role = str(shot.get("shot_role", "")).strip()
    if visual_mode == "profile_mood":
        return "a close-up of a woman with long dark hair under fluorescent station light"
    if visual_mode == "night_drive":
        return "a close-up of a singer in reflected night light with strong presence"
    if visual_mode == "window_reflection":
        return "a close-up of a singer through glass with reflected city lights"
    if visual_mode == "city_glance":
        return "a close-up of a woman turning toward the camera through city reflections"
    if visual_mode == "chorus_performance":
        return "a close-up of a singer facing the camera with neon reflections and vivid expression"
    if visual_mode == "neon_release":
        return "a close-up of a singer framed by neon reflections and moving city light"
    if visual_mode == "night_bridge":
        return "a close-up of a solitary woman with bridge lights behind her"
    if visual_mode == "memory_flash":
        return "a close-up portrait of a woman with soft reflected light and wind in her hair"
    if visual_mode == "bridge_transition":
        return "a close-up of a woman shifting from reflection to open night air"
    if role.startswith("chorus"):
        return "a close-up of a singer in a reflective city-pop portrait"
    return "a close-up of a stylish woman in an 80s city pop scene"



def _qwen_location_phrase(shot: dict) -> str:
    visual_mode = str(shot.get("visual_mode", "")).strip()
    mapping = {
        "profile_mood": "night station interior with dark glass panels",
        "night_drive": "night interior, passing street light, and reflected city glow",
        "window_reflection": "glass reflection close-up with city light spill",
        "city_glance": "night city glass reflection with passing shop lights",
        "chorus_performance": "glowing city light reflections with a nightlife backdrop",
        "neon_release": "night boulevard light reflected across glass and polished surfaces",
        "night_bridge": "bridge lights in soft focus behind the subject",
        "memory_flash": "soft city skyline or room-light reflection at dusk",
        "bridge_transition": "neon-lit transition between street light and glass reflection",
    }
    return mapping.get(visual_mode, "night city reflections")



def _qwen_palette_phrase(shot: dict, citypop_bible: dict) -> str:
    visual_mode = str(shot.get("visual_mode", "")).strip()
    if visual_mode in {"night_drive", "window_reflection", "night_bridge", "chorus_performance"}:
        return "deep blue and neon magenta palette"
    if visual_mode in {"memory_flash", "profile_mood"}:
        return "soft dusk violet and cool pink palette"
    if visual_mode in {"neon_release", "city_glance"}:
        return "deep blue and warm amber night palette"
    palette = [str(x).strip() for x in citypop_bible.get("palette", []) if str(x).strip()]
    return ", ".join(palette[:2])



def _qwen_styling_phrase(shot: dict) -> str:
    visual_mode = str(shot.get("visual_mode", "")).strip()
    if visual_mode in {"neon_release", "window_reflection", "night_drive", "chorus_performance", "city_glance"}:
        return "graphic reflective close-up styling"
    if visual_mode == "memory_flash":
        return "soft nostalgic reflective portrait styling"
    if visual_mode == "profile_mood":
        return "elegant station reflection styling"
    return "clean reflective city-pop styling"



def _qwen_framing_phrase(shot: dict) -> str:
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
        "bridge_transition": "graphic reflective close-up",
    }
    return mapping.get(visual_mode, "graphic close-up framing")
