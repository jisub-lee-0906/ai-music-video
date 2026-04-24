from __future__ import annotations


def build_idol_pop_prompt_seed(concept_text: str, style_bible: dict, shot: dict) -> str:
    return ", ".join(
        part
        for part in [
            "idol pop music video",
            str(concept_text or "").strip() or "bright idol pop city performance",
            "same protagonist, same glossy performance-night world",
            _subject_anchor(shot),
            _environment_anchor(shot),
            ", ".join(style_bible.get("palette", [])[:2]),
            "bright readable performance styling",
            "stable performer identity",
        ]
        if part
    )


def build_idol_pop_prompt_draft(shot: dict) -> str:
    return ", ".join(
        [
            _framing_phrase(shot),
            "motion-safe keyframe",
            "no layered collage",
            "no duplicate subject",
        ]
    )


def _subject_anchor(shot: dict) -> str:
    if str(shot.get("visual_mode", "")) == "chorus_front_lights":
        return "young performer facing camera with bright confident idol-pop energy"
    return "young performer with camera-readable face and polished stage confidence"


def _environment_anchor(shot: dict) -> str:
    mapping = {
        "boulevard_intro_glow": "glossy city boulevard with bright performance-night reflections",
        "city_chorus_walk": "late-night performance boulevard with polished urban light trails",
        "pre_chorus_lift": "bright city walkway with tightening stage-light reflections",
        "bridge_close_gloss": "close-in city glow with polished reflective signage",
        "chorus_front_lights": "open city performance lane with direct glossy backlight",
        "afterglow_stride": "confident late-night city stride with bright reflected lights",
    }
    return mapping.get(str(shot.get("visual_mode", "")), "bright modern city performance space with polished pop lighting")


def _framing_phrase(shot: dict) -> str:
    return {
        "establishing_wide": "wide performance-led frame with bright city geometry and one anchored subject",
        "performance_medium": "front-facing performance medium shot with bright readable face",
        "release_wide": "medium-wide release frame with polished city perspective and pop energy",
        "connective_medium": "clean medium shot with confident performer readability",
    }.get(str(shot.get("framing_intent", "")), "bright cinematic medium close-up")
