from __future__ import annotations


def build_alt_pop_prompt_seed(concept_text: str, style_bible: dict, shot: dict) -> str:
    return ", ".join(
        part
        for part in [
            "alt pop music video",
            str(concept_text or "").strip() or "alt pop rooftop night",
            "same protagonist, same modern night-world mood",
            _subject_anchor(shot),
            _environment_anchor(shot),
            ", ".join(style_bible.get("palette", [])[:2]),
            "clean cinematic styling",
            "stable character identity",
        ]
        if part
    )



def build_alt_pop_prompt_draft(shot: dict) -> str:
    return ", ".join(
        [
            _framing_phrase(shot),
            "motion-safe keyframe",
            "no layered collage",
            "no duplicate subject",
        ]
    )



def _subject_anchor(shot: dict) -> str:
    if str(shot.get("visual_mode", "")) == "chorus_front":
        return "young woman facing camera with assertive performance energy"
    return "young woman with sharp silhouette and controlled expression"



def _environment_anchor(shot: dict) -> str:
    mapping = {
        "rooftop_edge": "night rooftop with chrome spill and concrete geometry",
        "glass_corridor": "glass corridor with club-adjacent light spill",
        "pre_chorus_tension": "elevator lobby tension with mirrored steel and tightening city reflections",
        "bridge_glass": "glass skybridge with isolated backlight and drifting club spill",
        "chorus_front": "open rooftop edge with direct city backlight",
        "release_stride": "night street stride with chrome reflections",
    }
    return mapping.get(str(shot.get("visual_mode", "")), "modern urban night space with controlled edge lighting")



def _framing_phrase(shot: dict) -> str:
    return {
        "establishing_wide": "wide establishing frame with angular city geometry and one anchored subject",
        "performance_medium": "performance-led medium shot with clean edge light",
        "release_wide": "medium-wide release frame with strong city perspective",
    }.get(str(shot.get("framing_intent", "")), "clean cinematic medium close-up")
