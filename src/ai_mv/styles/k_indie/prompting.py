from __future__ import annotations


def build_k_indie_prompt_seed(concept_text: str, style_bible: dict, shot: dict) -> str:
    positive_concept = _positive_concept_anchor(concept_text)
    return ", ".join(
        part
        for part in [
            "k-indie music video",
            positive_concept or "k-indie intimate realism performance world",
            "same protagonist, same source-bound intimate world",
            _subject_anchor(shot),
            _environment_anchor(shot, positive_concept=positive_concept),
            _palette_anchor(style_bible, positive_concept=positive_concept),
            "naturalistic cinematic frame",
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
        return "solitary protagonist facing camera with intimate but steady performance energy"
    return "solitary protagonist with natural styling and quiet expression"



def _environment_anchor(shot: dict, *, positive_concept: str = "") -> str:
    visual_mode = str(shot.get("visual_mode", ""))
    if not _allows_rain_street_fixtures(positive_concept):
        return {
            "bookstore_window": "source-bound intimate window composition with quiet depth",
            "crosswalk_wait": "source-bound threshold wait with soft practical lamps",
            "pre_chorus_tension": "narrow source-bound threshold with hesitant light shimmer",
            "bridge_pause": "quiet pause point inside the established concept world",
            "chorus_portrait": "intimate portrait inside the established concept world",
            "bus_stop_afterglow": "late-section source-bound hold with soft release light",
        }.get(visual_mode, "intimate source-bound environment with muted realism")
    mapping = {
        "bookstore_window": "bookstore window with rain reflections and quiet street depth",
        "crosswalk_wait": "quiet crosswalk under soft night lamps",
        "pre_chorus_tension": "narrow side street with convenience-store spill and hesitant rain shimmer",
        "bridge_pause": "underpass bench pause with sparse traffic glow and damp concrete calm",
        "chorus_portrait": "rain-lit street portrait with intimate urban glow",
        "bus_stop_afterglow": "late bus stop with soft release light and light drizzle",
    }
    return mapping.get(visual_mode, "intimate rainy city environment with muted realism")


def _palette_anchor(style_bible: dict, *, positive_concept: str = "") -> str:
    palette = [str(item) for item in style_bible.get("palette", [])[:2]]
    if not _allows_rain_street_fixtures(positive_concept):
        palette = [item for item in palette if "rain" not in item.lower()]
    return ", ".join(palette)


def _allows_rain_street_fixtures(positive_concept: str) -> bool:
    text = str(positive_concept or "").lower()
    return any(token in text for token in ("book", "bookstore", "rain", "wet", "street", "crosswalk", "bus stop", "alley", "city", "night"))


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
        "establishing_wide": "observational wide frame with quiet street depth and one small subject",
        "performance_medium": "performance-led medium shot with intimate urban glow and calm edge separation",
        "release_wide": "release wide frame with source-bound atmosphere",
    }.get(str(shot.get("framing_intent", "")), "observational cinematic medium close-up")
