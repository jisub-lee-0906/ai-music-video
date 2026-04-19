from __future__ import annotations


def build_citypop_prompt_seed(concept_text: str, citypop_bible: dict, shot: dict) -> str:
    concept = _concept_seed_phrase(concept_text)
    continuity = _continuity_anchor(shot)
    subject = _still_subject_phrase(shot)
    location = _still_location_phrase(shot)
    palette = _still_palette_phrase(shot, citypop_bible)
    ordered_parts = _ordered_seed_parts(
        shot,
        concept=concept,
        continuity=continuity,
        subject=subject,
        location=location,
        palette=palette,
    )
    return ", ".join(
        part
        for part in [
            *ordered_parts,
            "clean cel shading",
            "single coherent night-drive world",
            "stable character identity",
            "film grain",
        ]
        if part
    )


def build_citypop_prompt_draft(shot: dict) -> str:
    framing = _still_framing_phrase(shot)
    composition = _still_composition_constraints(shot)
    return ", ".join(
        part
        for part in [
            framing,
            composition,
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


def _ordered_seed_parts(shot: dict, *, concept: str, continuity: str, subject: str, location: str, palette: str) -> list[str]:
    framing_intent = str(shot.get("framing_intent", "")).strip()
    if framing_intent in {"establishing_wide", "release_wide"}:
        return [concept, continuity, location, subject, palette]
    return [concept, continuity, subject, location, palette]


def _still_subject_phrase(shot: dict) -> str:
    visual_mode = str(shot.get("visual_mode", "")).strip()
    if visual_mode == "empty_boulevard_anchor":
        return "no foreground figure, only a barely noticeable distant human presence"
    if visual_mode == "curbside_silhouette":
        return "tiny curbside silhouette with the face turned away from camera"
    if visual_mode == "roadway_overview":
        return "tiny figure held at the curb edge beneath the city lights"
    if visual_mode == "street_establishing":
        return "one small figure under the city lights"
    if visual_mode == "profile_mood":
        return "young woman with long dark hair under fluorescent station light"
    if visual_mode == "night_drive":
        return "young woman driver with reflected night light and steady expression"
    if visual_mode == "window_reflection":
        return "young woman seen through side glass with reflected city lights"
    if visual_mode == "rain_window_detail":
        return "rain-streaked car window and a partial figure reflection"
    if visual_mode == "partial_figure_transition":
        return "partial figure crossing the frame with the face turned away"
    if visual_mode == "city_glance":
        return "young woman turning toward the camera through city reflections"
    if visual_mode == "chorus_performance":
        return "a close-up of a singer facing the camera with neon reflections and vivid expression"
    if visual_mode == "neon_release":
        return "young woman framed by neon reflections and moving city light"
    if visual_mode == "night_bridge":
        return "young woman with bridge lights behind her"
    if visual_mode == "bridge_overlook":
        return "small figure near the bridge lights seen from a slight distance"
    if visual_mode == "memory_flash":
        return "young woman in a soft afterglow portrait with wind in her hair"
    if visual_mode == "skyline_release":
        return "one small figure in the distance"
    if visual_mode == "bridge_transition":
        return "young woman shifting from reflection to open night air"
    return "young woman in a reflective summer night portrait"


def _still_location_phrase(shot: dict) -> str:
    visual_mode = str(shot.get("visual_mode", "")).strip()
    mapping = {
        "empty_boulevard_anchor": "near-empty rain-slick boulevard with dominant roadway depth and distant traffic glow",
        "curbside_silhouette": "rain-slick boulevard with passing traffic bands and dominant roadway depth",
        "roadway_overview": "rain-slick boulevard approach with broad roadway depth and neon traffic glow",
        "street_establishing": "rainy neon boulevard at dusk with long wet-road reflections",
        "profile_mood": "night station interior with dark glass panels",
        "night_drive": "night expressway interior with passing street light and reflected city glow",
        "window_reflection": "car side window with layered reflections and city light spill",
        "rain_window_detail": "rain-streaked side glass with streetlight reflections in close succession",
        "partial_figure_transition": "wet boulevard edge with passing reflections and partial body motion",
        "city_glance": "night boulevard glass reflection with passing shop lights",
        "chorus_performance": "glowing city light reflections with a nightlife backdrop",
        "neon_release": "night boulevard light across wet street and polished surfaces",
        "night_bridge": "bridge lights in soft focus behind the subject",
        "bridge_overlook": "bridge promenade with wet pavement and receding pink bridge lights",
        "memory_flash": "soft city skyline reflection at dusk",
        "skyline_release": "rainy neon skyline boulevard at dusk",
        "bridge_transition": "transition between street light and reflective glass in the same city",
    }
    return mapping.get(visual_mode, "night city reflections")


def _still_palette_phrase(shot: dict, citypop_bible: dict) -> str:
    visual_mode = str(shot.get("visual_mode", "")).strip()
    if visual_mode in {"night_drive", "window_reflection", "night_bridge", "chorus_performance"}:
        return "deep blue and neon magenta palette"
    if visual_mode in {"empty_boulevard_anchor", "curbside_silhouette", "roadway_overview", "street_establishing", "skyline_release"}:
        return "soft dusk violet and neon pink palette"
    if visual_mode in {"memory_flash", "profile_mood"}:
        return "soft dusk violet and cool pink palette"
    if visual_mode in {"neon_release", "city_glance"}:
        return "deep blue and warm amber night palette"
    palette = [str(x).strip() for x in citypop_bible.get("palette", []) if str(x).strip()]
    return ", ".join(palette[:2])


def _still_framing_phrase(shot: dict) -> str:
    framing_intent = str(shot.get("framing_intent", "")).strip()
    visual_mode = str(shot.get("visual_mode", "")).strip()
    specialized_mapping = {
        "empty_boulevard_anchor": "world-first establishing frame with the boulevard and city light as the unquestioned subject",
        "curbside_silhouette": "world-first establishing frame with boulevard depth and an incidental edge-held silhouette",
        "roadway_overview": "wide establishing frame with roadway-led depth and a tiny edge-held subject",
        "street_establishing": "wide establishing frame with a small subject and dominant city perspective",
        "rain_window_detail": "detail insert framing through rain-streaked reflective glass",
        "partial_figure_transition": "partial-figure transition frame with the environment carrying most of the image",
        "bridge_overlook": "observational medium shot with bridge-led depth and a smaller subject",
        "skyline_release": "wide release frame with skyline-led negative space",
    }
    if visual_mode in specialized_mapping:
        return specialized_mapping[visual_mode]
    intent_mapping = {
        "establishing_wide": "wide establishing frame with a small subject and dominant city perspective",
        "hero_medium": "hero medium shot with clear environment context",
        "connective_medium": "environment-led medium shot with connective framing",
        "performance_closeup": "bold front-facing close-up",
        "release_wide": "wide release frame with skyline-led negative space",
    }
    if framing_intent in intent_mapping:
        return intent_mapping[framing_intent]
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



def _still_composition_constraints(shot: dict) -> str:
    framing_intent = str(shot.get("framing_intent", "")).strip()
    visual_mode = str(shot.get("visual_mode", "")).strip()
    if visual_mode == "empty_boulevard_anchor":
        return "no foreground figure, only a tiny distant human trace if any, large negative space, vanishing point separated from any human presence, roadway and city light dominate the frame"
    if visual_mode == "curbside_silhouette":
        return "subject on the extreme outer edge, subject barely legible, no readable face, large negative space, vanishing point separated from the subject, roadway and city light dominate the frame"
    if visual_mode == "roadway_overview":
        return "off-center composition, subject on the outer third, large negative space, no direct face toward camera, vanishing point separated from the subject"
    if framing_intent in {"establishing_wide", "release_wide"} or visual_mode in {"street_establishing", "skyline_release"}:
        return "off-center composition, large negative space, small figure emphasis, no direct face toward camera"
    if visual_mode == "rain_window_detail":
        return "detail-first composition, partial figure only, no hero framing, no direct face toward camera"
    if visual_mode in {"partial_figure_transition", "bridge_overlook"}:
        return "partial figure only, off-center subject, no direct face toward camera, environment dominates the frame"
    return ""
