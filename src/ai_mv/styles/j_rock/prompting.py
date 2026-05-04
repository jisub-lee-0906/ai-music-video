from __future__ import annotations


def build_j_rock_prompt_seed(concept_text: str, style_bible: dict, shot: dict) -> str:
    return ", ".join(
        part
        for part in [
            "j-rock music video",
            str(concept_text or "").strip() or "j-rock live-house night drive",
            "same protagonist, same high-energy night world",
            _subject_anchor(shot),
            _environment_anchor(shot),
            ", ".join(style_bible.get("palette", [])[:2]),
            "performance-forward cinematic frame",
            "stable character identity",
        ]
        if part
    )



def build_j_rock_prompt_draft(shot: dict) -> str:
    return ", ".join(
        [
            _framing_phrase(shot),
            "motion-safe keyframe",
            "no layered collage",
            "no duplicate subject",
        ]
    )



def _subject_anchor(shot: dict) -> str:
    if str(shot.get("visual_mode", "")) == "chorus_charge":
        return "solitary protagonist facing camera with high-energy performance expression"
    return "solitary protagonist with sharp silhouette and driven performance posture"



def _environment_anchor(shot: dict) -> str:
    mapping = {
        "live_house_entry": "live house alley with amp glow and wet asphalt",
        "amp_corridor": "backstage corridor with stage spill and hard night contrast",
        "pre_chorus_lift": "backstage stairwell with rising stage spill and tightening electric haze",
        "bridge_break": "service alley break with distant stage rumble and isolated sodium backlight",
        "chorus_charge": "performance-forward night street with electric backlight",
        "outro_stride": "wet asphalt release path with receding stage light",
    }
    return mapping.get(str(shot.get("visual_mode", "")), "performance-led night environment with electric motion energy")



def _framing_phrase(shot: dict) -> str:
    return {
        "establishing_wide": "wide establishing frame with performance-world context and one driven subject",
        "performance_medium": "performance-led medium shot with strong stage-adjacent energy",
        "release_wide": "release wide frame with receding lights and performance afterimage",
    }.get(str(shot.get("framing_intent", "")), "performance-forward cinematic medium close-up")
