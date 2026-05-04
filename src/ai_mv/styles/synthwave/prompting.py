from __future__ import annotations


def build_synthwave_prompt_seed(concept_text: str, style_bible: dict, shot: dict) -> str:
    concept = _normalize_concept_text(concept_text)
    continuity = _continuity_anchor(shot)
    subject = _subject_anchor(shot)
    environment = _environment_anchor(shot)
    palette = _palette_phrase(style_bible)
    return ", ".join(
        part
        for part in [
            "retro synthwave music video",
            concept,
            continuity,
            subject,
            environment,
            palette,
            "retro-futurist cinematic frame",
            "single coherent night-drive world",
            "stable character identity",
            "clean cinematic composition",
            "analog glow",
        ]
        if part
    )


def build_synthwave_prompt_draft(shot: dict) -> str:
    framing_intent = str(shot.get("framing_intent", "")).strip()
    intent_mapping = {
        "establishing_wide": "wide establishing frame with stable skyline depth and one anchored subject",
        "hero_medium": "hero medium shot with controlled road perspective and visible environment",
        "connective_medium": "environment-led medium shot with one dominant subject and stable depth",
        "performance_medium": "performance-led medium shot with stable skyline depth and visible world context",
        "performance_medium": "performance-led medium shot with stable skyline depth and visible world context",
        "release_wide": "medium-wide release frame with one anchored silhouette and clean road perspective",
    }
    if framing_intent in intent_mapping:
        framing = intent_mapping[framing_intent]
    else:
        visual_mode = str(shot.get("visual_mode", "")).strip()
        framing = {
            "laser_horizon": "low-angle horizon framing with stable vanishing lines",
            "neon_highway": "windshield-side close-up with controlled road perspective",
            "mirror_glass": "single-subject reflection close-up with clean glass geometry",
            "dashboard_pulse": "cockpit close-up with restrained console glow",
            "grid_surge": "front-facing hero frame with stable skyline depth",
            "neon_run": "tracking boulevard composition with one dominant subject",
            "skyline_bloom": "wide skyline release with one anchored silhouette",
            "tunnel_reveal": "tunnel transition frame with single-scene depth",
            "afterglow_escape": "afterglow portrait with clean edge separation and no overlays",
        }.get(visual_mode, "single-scene synthwave cinematic close-up")
    return ", ".join(
        [
            framing,
            "no layered collage",
            "no abstract overlay",
            "no duplicate subject",
            "motion-safe keyframe",
        ]
    )


def _normalize_concept_text(concept_text: str) -> str:
    text = str(concept_text or "").strip()
    return text or "retro synthwave night-drive music video"


def _continuity_anchor(shot: dict) -> str:
    role = str(shot.get("shot_role", "")).strip()
    mapping = {
        "intro_glide": "same night, same expressway journey, opening approach",
        "intro_approach": "same night, same expressway journey, city lights approaching",
        "verse_cruise": "same protagonist, same vehicle journey, controlled forward motion",
        "verse_reflection": "same protagonist, same vehicle interior, reflected neon continuity",
        "verse_swerve": "same protagonist, same roadway, tension rising without scene change",
        "verse_afterimage": "same protagonist, same night world, lingering afterimage of motion",
        "prechorus_charge": "same night, same route, energy tightening before the hook",
        "prechorus_release": "same subject, same route, anticipation peaks without world change",
        "chorus_breakout": "same protagonist, same boulevard, hook arrives in the same world",
        "chorus_cruise": "same protagonist, same boulevard, release continues with wider motion",
        "chorus_lift": "same protagonist, same skyline, emotional lift without identity drift",
        "chorus_afterburn": "same protagonist, same skyline, lingering afterburn of the hook",
        "bridge_descent": "same protagonist, same city, bridge moment turns inward without cutting worlds",
        "bridge_escape": "same protagonist, same city, transition out of the bridge with continuity intact",
        "outro_fade": "same protagonist, same night, afterglow fading toward dawn",
        "outro_tail": "same protagonist, same night, final tail lights receding in one world",
    }
    return mapping.get(role, "same protagonist, same night-drive world, continuity preserved")


def _subject_anchor(shot: dict) -> str:
    visual_mode = str(shot.get("visual_mode", "")).strip()
    mapping = {
        "laser_horizon": "solitary protagonist with a sleek silhouette",
        "neon_highway": "solitary driver with steady gaze",
        "mirror_glass": "solitary protagonist reflected in side glass",
        "dashboard_pulse": "solitary protagonist in the cockpit with focused expression",
        "grid_surge": "solitary performer with direct eye contact",
        "neon_run": "solitary protagonist in motion with rim light",
        "skyline_bloom": "solitary protagonist silhouette against the skyline",
        "tunnel_reveal": "solitary protagonist framed by tunnel light",
        "afterglow_escape": "solitary protagonist in a calm afterglow portrait",
    }
    return mapping.get(visual_mode, "solitary protagonist with stable synthwave styling")


def _environment_anchor(shot: dict) -> str:
    visual_mode = str(shot.get("visual_mode", "")).strip()
    mapping = {
        "laser_horizon": "elevated expressway, distant skyline, neon horizon lines",
        "neon_highway": "night expressway with reflective asphalt and cyan-magenta light trails",
        "mirror_glass": "car side window, reflected skyline, wet urban light",
        "dashboard_pulse": "vehicle interior, dashboard glow, night roadway beyond the glass",
        "grid_surge": "open boulevard, skyline depth, wet road reflections",
        "neon_run": "wide boulevard, moving tail lights, deep city perspective",
        "skyline_bloom": "glowing skyline, wet concrete, clear road perspective",
        "tunnel_reveal": "city tunnel mouth, receding lights, stable vanishing point",
        "afterglow_escape": "quiet overpass, fading tail lights, soft neon afterglow",
    }
    return mapping.get(visual_mode, "same urban night-drive setting with stable road perspective")


def _palette_phrase(style_bible: dict) -> str:
    palette = [str(x).strip() for x in style_bible.get("palette", [])[:3] if str(x).strip()]
    return ", ".join(palette)

