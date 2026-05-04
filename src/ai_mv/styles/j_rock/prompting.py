from __future__ import annotations


def build_j_rock_prompt_seed(concept_text: str, style_bible: dict, shot: dict) -> str:
    positive_concept = _positive_concept_anchor(concept_text)
    return ", ".join(
        part
        for part in [
            "j-rock music video",
            positive_concept or "j-rock performance world",
            "same protagonist, same source-bound high-energy world",
            _subject_anchor(shot),
            _environment_anchor(shot, positive_concept=positive_concept),
            _palette_anchor(style_bible, positive_concept=positive_concept),
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



def _environment_anchor(shot: dict, *, positive_concept: str = "") -> str:
    visual_mode = str(shot.get("visual_mode", ""))
    if not _allows_stage_wet_fixtures(positive_concept):
        return {
            "live_house_entry": "source-bound performance threshold with hard contrast",
            "amp_corridor": "directional-light path with hard contrast",
            "pre_chorus_lift": "rising source-bound path with tightening electric haze",
            "bridge_break": "isolated pause point inside the established concept world",
            "chorus_charge": "performance-forward concept world with electric backlight",
            "outro_stride": "source-bound release path with receding light",
        }.get(visual_mode, "performance-led source-bound environment with electric motion energy")
    mapping = {
        "live_house_entry": "live house alley with amp glow and wet asphalt",
        "amp_corridor": "backstage corridor with stage spill and hard night contrast",
        "pre_chorus_lift": "backstage stairwell with rising stage spill and tightening electric haze",
        "bridge_break": "service alley break with distant stage rumble and isolated sodium backlight",
        "chorus_charge": "performance-forward night street with electric backlight",
        "outro_stride": "wet asphalt release path with receding stage light",
    }
    return mapping.get(visual_mode, "performance-led night environment with electric motion energy")


def _palette_anchor(style_bible: dict, *, positive_concept: str = "") -> str:
    palette = [str(item) for item in style_bible.get("palette", [])[:2]]
    if not _allows_stage_wet_fixtures(positive_concept):
        palette = [item for item in palette if not any(token in item.lower() for token in ("rain", "wet", "reflection"))]
    return ", ".join(palette)


def _allows_stage_wet_fixtures(positive_concept: str) -> bool:
    text = str(positive_concept or "").lower()
    return any(token in text for token in ("live house", "stage", "backstage", "alley", "street", "city", "night", "rain", "wet", "reflection", "asphalt"))


def _positive_concept_anchor(concept_text: str) -> str:
    text = str(concept_text or "").strip()
    if not text:
        return ""
    pieces: list[str] = []
    for raw_part in text.split(","):
        part = raw_part.strip()
        if not part:
            continue
        lowered = part.lower()
        if lowered.startswith(("no ", "without ", "avoid ", "never ")):
            continue
        pieces.append(part)
    return ", ".join(pieces)



def _framing_phrase(shot: dict) -> str:
    return {
        "establishing_wide": "wide establishing frame with performance-world context and one driven subject",
        "performance_medium": "performance-led medium shot with strong stage-adjacent energy",
        "release_wide": "release wide frame with receding lights and performance afterimage",
    }.get(str(shot.get("framing_intent", "")), "performance-forward cinematic medium close-up")
