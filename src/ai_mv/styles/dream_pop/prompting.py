from __future__ import annotations


def build_dream_pop_prompt_seed(concept_text: str, style_bible: dict, shot: dict) -> str:
    return ", ".join(
        part
        for part in [
            "dream pop music video",
            str(concept_text or "").strip() or "dream pop night vignette",
            "same protagonist, same soft night world",
            _subject_anchor(shot),
            _environment_anchor(shot),
            ", ".join(style_bible.get("palette", [])[:2]),
            "ethereal cinematic frame",
            "stable character identity",
        ]
        if part
    )



def build_dream_pop_prompt_draft(shot: dict) -> str:
    return ", ".join(
        [
            _framing_phrase(shot),
            "motion-safe keyframe",
            "no layered collage",
            "no abstract overlay",
        ]
    )



def _subject_anchor(shot: dict) -> str:
    if str(shot.get("visual_mode", "")) == "chorus_bloom":
        return "solitary protagonist facing camera with softened afterglow expression"
    return "solitary protagonist with soft silhouette and calm expression"



def _environment_anchor(shot: dict) -> str:
    mapping = {
        "moonlit_overpass": "moonlit overpass with misty depth and reflective air",
        "window_haze": "soft window haze with city bokeh and pearl reflections",
        "pre_chorus_lift": "soft stairwell glow with suspended haze and rising moonlit reflections",
        "bridge_hush": "quiet side street bridge with softened fog pockets and distant silver lamps",
        "chorus_bloom": "open skyline bloom with dreamy light spill",
        "afterglow_walk": "quiet afterglow street with silver haze",
    }
    return mapping.get(str(shot.get("visual_mode", "")), "soft nocturnal environment with dreamy haze")



def _framing_phrase(shot: dict) -> str:
    return {
        "establishing_wide": "soft wide frame with hazy depth and one anchored subject",
        "performance_medium": "performance-led medium shot with gentle bloom and stable edge separation",
        "release_wide": "release wide frame with airy negative space",
    }.get(str(shot.get("framing_intent", "")), "soft cinematic close-up with stable scene depth")
