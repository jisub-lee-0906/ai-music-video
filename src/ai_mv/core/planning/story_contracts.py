from __future__ import annotations


def build_story_contract(shot: dict, *, previous_shot: dict | None = None, concept_text: str = "") -> dict:
    section_type = _clean(shot.get("section_type")) or "section"
    shot_role = _clean(shot.get("shot_role")) or "shot"
    visual_mode = _clean(shot.get("visual_mode")) or "visual beat"
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
    return {
        "why_this_shot": (
            f"This {section_type} {shot_role} exists to turn the {story_function} story beat into a readable action: {visual_event}."
        ),
        "protagonist_action": protagonist_action,
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
    lower = str(text or "").lower()
    motifs: list[str] = []
    keyword_map = [
        (("train", "station", "subway", "전철", "지하철"), "station timing and platform light"),
        (("rain", "wet", "umbrella", "비"), "rain/reflection texture"),
        (("neon", "city", "night", "밤", "도시"), "night-city light"),
        (("desert", "dune", "sand"), "desert horizon space"),
        (("sunrise", "dawn", "새벽"), "sunrise transition light"),
        (("radio", "tower", "antenna"), "radio tower signal motif"),
        (("ocean", "sea", "beach", "바다"), "ocean horizon motif"),
        (("room", "bedroom", "apartment", "방"), "interior personal-object motif"),
    ]
    for keys, motif in keyword_map:
        if any(key in lower for key in keys):
            motifs.append(motif)
    if not motifs:
        important_words = [word.strip(".,:;!?()[]{}") for word in lower.split() if len(word.strip(".,:;!?()[]{}")) >= 5]
        if important_words:
            motifs.append("concept motif: " + " / ".join(important_words[:3]))
    return "; ".join(dict.fromkeys(motifs)) if motifs else "the concept's signature visual motif"


def _clean(value: object) -> str:
    return str(value or "").strip()
