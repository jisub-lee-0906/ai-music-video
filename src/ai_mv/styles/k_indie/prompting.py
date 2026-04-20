from __future__ import annotations


def build_k_indie_prompt_seed(concept_text: str, style_bible: dict, shot: dict) -> str:
    return ", ".join(
        part
        for part in [
            "k-indie music video",
            str(concept_text or "").strip() or "k-indie rainy street vignette",
            "same protagonist, same intimate city night",
            _subject_anchor(shot),
            _environment_anchor(shot),
            ", ".join(style_bible.get("palette", [])[:2]),
            "naturalistic anime frame",
            "stable character identity",
        ]
        if part
    )



def build_k_indie_prompt_draft(shot: dict) -> str:
    return ", ".join(
        [
            _framing_phrase(shot),
            "motion-safe keyframe",
            "no layered collage",
            "no abstract overlay",
        ]
    )



def _subject_anchor(shot: dict) -> str:
    if str(shot.get("visual_mode", "")) == "chorus_portrait":
        return "young woman facing camera with intimate but steady performance energy"
    return "young woman with natural styling and quiet expression"



def _environment_anchor(shot: dict) -> str:
    mapping = {
        "bookstore_window": "bookstore window with rain reflections and quiet street depth",
        "crosswalk_wait": "quiet crosswalk under soft night lamps",
        "chorus_portrait": "rain-lit street portrait with intimate urban glow",
        "bus_stop_afterglow": "late bus stop with soft afterglow and light drizzle",
    }
    return mapping.get(str(shot.get("visual_mode", "")), "intimate rainy city environment with muted realism")



def _framing_phrase(shot: dict) -> str:
    return {
        "establishing_wide": "observational wide frame with quiet street depth and one small subject",
        "performance_closeup": "front-facing close-up with intimate urban glow and calm edge separation",
        "release_wide": "release wide frame with soft rain atmosphere",
    }.get(str(shot.get("framing_intent", "")), "observational cinematic medium close-up")
