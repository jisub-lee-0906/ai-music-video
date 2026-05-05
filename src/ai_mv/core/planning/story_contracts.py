from __future__ import annotations


def build_story_contract(shot: dict, *, previous_shot: dict | None = None, concept_text: str = "") -> dict:
    section_type = _clean(shot.get("section_type")) or "section"
    shot_role = _clean(shot.get("shot_role")) or "shot"
    visual_mode = _section_alignment_visual_token(shot, concept_text=concept_text) or "visual beat"
    story_function = _clean(shot.get("story_function")) or "advance"
    visual_event = _clean(shot.get("visual_event")) or f"make the {story_function} beat visible"
    emotional_state = _clean(shot.get("emotional_state")) or "progressing"
    required_change = _clean(shot.get("required_change_from_previous")) or "change action, framing, or visual emphasis from the previous shot"
    payoff_requirement = _clean(shot.get("payoff_requirement"))
    concept_motif = _concept_motif(concept_text)
    previous_function = _clean(previous_shot.get("story_function")) if isinstance(previous_shot, dict) else "sequence start"

    protagonist_action = _protagonist_action(
        story_function=story_function,
        section_type=section_type,
        visual_event=visual_event,
        concept_motif=concept_motif,
        emotional_state=emotional_state,
    )
    visual_payoff = _visual_payoff(
        story_function=story_function,
        visual_event=visual_event,
        payoff_requirement=payoff_requirement,
        concept_motif=concept_motif,
    )
    story_action_grammar = _clean(shot.get("story_action_grammar"))
    return {
        "why_this_shot": (
            f"This {section_type} {shot_role} exists to turn the {story_function} story beat into a readable action: {visual_event}."
        ),
        "protagonist_action": protagonist_action,
        "story_action_grammar": story_action_grammar,
        "section_alignment": (
            f"Align with the {section_type} section by showing {emotional_state} energy through {visual_mode}, not a detachable generic mood shot."
        ),
        "progression_from_previous": (
            f"Progress from {previous_function} by {required_change}; keep continuity while making a new narrative beat."
        ),
        "visual_payoff": visual_payoff,
        "anti_repetition_constraint": (
            f"Avoid repeating the same centered walking/performance pose; change at least one of action, camera distance, location function, or symbolic motif using {concept_motif}."
        ),
    }


def story_contract_prompt_tokens(story_contract: dict | None) -> list[str]:
    if not isinstance(story_contract, dict):
        return []
    labels = {
        "why_this_shot": "shot purpose",
        "protagonist_action": "protagonist action",
        "story_action_grammar": "story action grammar",
        "section_alignment": "section alignment",
        "progression_from_previous": "story progression",
        "visual_payoff": "visual payoff",
        "anti_repetition_constraint": "anti repetition",
    }
    tokens: list[str] = []
    for key, label in labels.items():
        value = _clean(story_contract.get(key))
        if value:
            tokens.append(f"{label}: {value}")
    return tokens


def _protagonist_action(*, story_function: str, section_type: str, visual_event: str, concept_motif: str, emotional_state: str) -> str:
    if story_function == "wound_setup":
        verb = "holds back and reveals the starting wound"
    elif story_function == "search":
        verb = "actively follows a trace instead of posing"
    elif story_function == "threshold":
        verb = "pauses at a visible decision point"
    elif story_function == "release":
        verb = "moves forward with clearer hook energy"
    elif story_function == "payoff":
        verb = "shows a changed state or decision"
    else:
        verb = "does a readable action that advances the beat"
    return f"The protagonist {verb} in the {section_type}, using {concept_motif} as the visible cue for {emotional_state}: {visual_event}."


def _visual_payoff(*, story_function: str, visual_event: str, payoff_requirement: str, concept_motif: str) -> str:
    if payoff_requirement:
        return f"Pay off the beat with {payoff_requirement}, expressed through {concept_motif}."
    if story_function == "release":
        return f"The hook should visibly open up through {concept_motif}, action, light, or motion rather than repeating the setup."
    if story_function == "payoff":
        return f"The final image should leave a changed afterimage through {concept_motif}: {visual_event}."
    return f"The shot must leave a readable micro-payoff through {concept_motif}: {visual_event}."


def _concept_motif(text: str) -> str:
    lower = _positive_concept_text(text)
    motifs: list[str] = []
    keyword_map = [
        (("train", "station", "subway", "전철", "지하철"), "station timing and platform light"),
        (("rain", "wet", "umbrella", "비"), "rain/reflection texture"),
        (("neon", "urban", "도시"), "urban night light"),
        (("desert", "dune", "sand"), "desert horizon space"),
        (("greenhouse", "glasshouse", "seedling", "seedlings"), "greenhouse glasshouse motif"),
        (("forest", "mossy", "moss", "pier"), "forest pier motif"),
        (("underwater", "aquarium", "glass tunnel"), "underwater aquarium motif"),
        (("arctic", "ice", "snow"), "arctic ice motif"),
        (("meadow", "grass", "kites"), "meadow grass motif"),
        (("lighthouse", "cliff", "coast"), "lighthouse cliff motif"),
        (("sunrise", "dawn", "새벽"), "sunrise transition light"),
        (("ocean", "sea", "beach", "바다"), "ocean horizon motif"),
        (("room", "bedroom", "apartment", "방"), "interior personal-object motif"),
    ]
    for keys, motif in keyword_map:
        if any(key in lower for key in keys):
            motifs.append(motif)
    has_tower_source = any(token in lower for token in ("tower", "antenna"))
    has_signal_source = "signal" in lower
    has_radio_source = "radio" in lower
    if has_tower_source and (has_radio_source or has_signal_source):
        motifs.append("radio tower signal motif")
    elif has_tower_source:
        motifs.append("distant tower motif")
    elif has_signal_source:
        motifs.append("source-bound signal motif")
    elif has_radio_source:
        motifs.append("radio object motif")
    if not motifs:
        important_words = [word.strip(".,:;!?()[]{}") for word in lower.split() if len(word.strip(".,:;!?()[]{}")) >= 5]
        if important_words:
            motifs.append("concept motif: " + " / ".join(important_words[:3]))
    return "; ".join(dict.fromkeys(motifs)) if motifs else "the concept's signature visual motif"


def _section_alignment_visual_token(shot: dict, *, concept_text: str = "") -> str:
    raw_visual_mode = _clean(shot.get("visual_mode"))
    world_anchor = _clean(shot.get("world_anchor")).lower()
    if "avoid urban or street-location substitution" in world_anchor:
        return "source-bound section beat"
    lower = " ".join(
        _clean(value).lower()
        for value in (
            _positive_concept_text(concept_text),
            shot.get("world_anchor"),
            shot.get("story_action_grammar"),
            shot.get("visual_event"),
        )
    )
    if "desert" in lower and any(token in lower for token in ("radio", "signal", "tower", "antenna")):
        progression = shot.get("narrative_progression") if isinstance(shot.get("narrative_progression"), dict) else {}
        beat_role = _clean(progression.get("beat_role")) or _clean(shot.get("story_function")) or _clean(shot.get("section_type"))
        return f"desert radio {beat_role.replace('_', ' ')} beat" if beat_role else "desert radio beat"
    return _visual_mode_label(raw_visual_mode)


def _visual_mode_label(raw_visual_mode: str) -> str:
    labels = {
        "rooftop_edge": "high-edge section beat",
        "glass_corridor": "layered-passage section beat",
        "bridge_glass": "layered bridge transition beat",
        "release_stride": "release stride beat",
        "pre_chorus_tension": "pre-chorus tension beat",
        "chorus_front": "front-facing chorus beat",
        "neon_highway": "long-path section beat",
        "crosswalk_wait": "threshold wait beat",
        "live_house_entry": "performance-threshold beat",
        "amp_corridor": "directional-light path beat",
        "window_haze": "soft-haze section beat",
        "bookstore_window": "world-first window section beat",
        "rain_window_detail": "source-bound detail section beat",
        "window_reflection": "source-bound window detail beat",
        "bus_stop_afterglow": "late-section release hold beat",
        "afterglow_hold": "late-section release hold beat",
    }
    lower = raw_visual_mode.lower()
    if lower in labels:
        return labels[lower]
    if "_" in raw_visual_mode:
        return raw_visual_mode.replace("_", " ") + " beat"
    return raw_visual_mode



def _clean(value: object) -> str:
    return str(value or "").strip()



def _positive_concept_text(text: object) -> str:
    pieces: list[str] = []
    for raw_part in str(text or "").lower().split(","):
        part = raw_part.strip()
        if not part:
            continue
        if part.startswith(("no ", "without ", "avoid ", "never ")):
            continue
        pieces.append(part)
    return ", ".join(pieces)
