from __future__ import annotations


def build_alt_pop_prompt_seed(concept_text: str, style_bible: dict, shot: dict) -> str:
    positive_concept = _positive_concept_anchor(concept_text)
    return ", ".join(
        part
        for part in [
            "alt pop music video",
            positive_concept or "alt pop performance world",
            _world_continuity_anchor(shot),
            _subject_anchor(shot),
            _environment_anchor(shot, positive_concept=positive_concept),
            _palette_anchor(style_bible, shot),
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
        return "same solitary lead protagonist facing camera with assertive performance energy"
    return "same solitary lead protagonist with sharp silhouette and controlled expression"



def _world_continuity_anchor(shot: dict) -> str:
    world_anchor = str(shot.get("world_anchor", "")).strip()
    if _is_desert_radio_world(world_anchor):
        return "same protagonist, same desert radio sunrise world"
    return "same protagonist, same concept-led performance world"



def _palette_anchor(style_bible: dict, shot: dict) -> str:
    world_anchor = str(shot.get("world_anchor", "")).strip()
    if _is_desert_radio_world(world_anchor):
        return "sunrise amber, desert blue shadow"
    return ", ".join(style_bible.get("palette", [])[:2])



def _environment_anchor(shot: dict, *, positive_concept: str = "") -> str:
    world_anchor = str(shot.get("world_anchor", "")).strip()
    if _is_desert_radio_world(world_anchor):
        return _desert_radio_environment_anchor(shot)
    if _allows_alt_pop_urban_environment(positive_concept, world_anchor):
        mapping = {
            "rooftop_edge": "night rooftop with chrome spill and concrete geometry",
            "glass_corridor": "glass corridor with club-adjacent light spill",
            "pre_chorus_tension": "elevator lobby tension with mirrored steel and tightening city reflections",
            "bridge_glass": "glass skybridge with isolated backlight and drifting club spill",
            "chorus_front": "open rooftop edge with direct city backlight",
            "release_stride": "night street stride with chrome reflections",
        }
    else:
        mapping = {
            "rooftop_edge": "elevated edge composition with controlled geometry",
            "glass_corridor": "transparent passage composition with controlled light spill",
            "pre_chorus_tension": "tightening threshold composition with mirrored texture",
            "bridge_glass": "isolated translucent passage with soft backlight",
            "chorus_front": "open front-facing composition with direct backlight",
            "release_stride": "forward stride composition with clean reflective texture",
        }
    return mapping.get(str(shot.get("visual_mode", "")), "modern style space with controlled edge lighting")


def _allows_alt_pop_urban_environment(positive_concept: str, world_anchor: str) -> bool:
    text = f"{positive_concept} {world_anchor}".lower()
    return any(token in text for token in ("city", "urban", "street", "rooftop", "club", "corridor", "lobby", "neon", "chrome", "night drive"))



def _desert_radio_environment_anchor(shot: dict) -> str:
    progression = shot.get("narrative_progression") if isinstance(shot.get("narrative_progression"), dict) else {}
    beat_role = str(progression.get("beat_role", "") or shot.get("beat_role", "")).strip()
    return {
        "setup": "wide desert dune horizon with a silent handheld radio and pre-sunrise air",
        "search": "open dunes with a faint radio signal light and low sunrise rim light",
        "approach": "wind-shaped desert path toward a distant antenna silhouette",
        "discovery": "distant radio tower revealed across the dunes under growing dawn light",
        "confrontation": "radio tower signal zone with harsh static light against the sunrise horizon",
        "recognition": "close desert signal moment with the radio held away from the protagonist face",
        "release": "quiet sunrise desert horizon with the radio lowered or left behind",
    }.get(beat_role, "desert dune radio-signal world with sunrise horizon light")



def _is_desert_radio_world(text: str) -> bool:
    lower = str(text or "").lower()
    return any(token in lower for token in ("desert", "dune", "sand")) and any(
        token in lower for token in ("radio", "tower", "signal", "antenna")
    )



def _positive_concept_anchor(concept_text: str) -> str:
    """Keep user-desired positive motifs but drop explicit negative clauses from generation prompts."""

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
    if _is_desert_radio_world(str(shot.get("world_anchor", ""))):
        return {
            "establishing_wide": "wide desert establishing frame with one anchored subject and readable radio motif",
            "performance_medium": "medium desert performance frame with clear radio-hand pose and sunrise edge light",
            "release_wide": "medium-wide desert release frame with open horizon and one anchored subject",
        }.get(str(shot.get("framing_intent", "")), "clean cinematic desert medium close-up with stable scene depth")
    return {
        "establishing_wide": "wide establishing frame with angular style geometry and one anchored subject",
        "performance_medium": "performance-led medium shot with clean edge light",
        "release_wide": "medium-wide release frame with strong style perspective",
    }.get(str(shot.get("framing_intent", "")), "clean cinematic medium close-up")
