from __future__ import annotations

import re
from collections.abc import Iterable

_NEGATIVE_PREFIX_RE = re.compile(r"^(no|without|avoid|never|exclude|do not)\b\s*", re.I)
_NEGATIVE_CLAUSE_RE = re.compile(r"\b(no|without|avoid|never|exclude|do not|not a)\b\s+([^,.;]+)", re.I)
_META_LABEL_RE = re.compile(
    r"\b(shot purpose|story function|story visual event|section alignment|story progression|visual payoff|"
    r"anti repetition|protagonist action|story action grammar|narrative beat role|narrative motif state|"
    r"narrative visible change|narrative pose intent|narrative motion intent|narrative continuity|payoff requirement):\s*",
    re.I,
)

_DEFAULT_VISUAL_NEGATIVES = [
    "duplicate person",
    "crowd",
    "second protagonist",
    "collage",
    "split screen",
    "text overlay",
    "identity drift",
    "face morphing",
    "extra limbs",
]


def parse_user_intent_contract(concept_text: str) -> dict:
    """Parse user-facing concept text into positive visual intent and forbidden clauses.

    This parser is intentionally conservative: it does not attempt to fully rewrite the
    user's concept. It only separates explicit negative clauses so they do not leak into
    positive model prompts.
    """
    raw = " ".join(str(concept_text or "").split()).strip()
    clauses = [part.strip(" .") for part in raw.split(",") if part.strip(" .")]
    positive_clauses: list[str] = []
    forbidden: list[str] = []
    for clause in clauses:
        if _NEGATIVE_PREFIX_RE.search(clause):
            forbidden.extend(_forbidden_terms_from_clause(clause))
        else:
            positive_clauses.append(clause)
    positive_text = ", ".join(positive_clauses)
    lower = positive_text.lower()
    motifs = _motifs_from_positive_text(lower)
    return {
        "source_text": raw,
        "positive_text": positive_text,
        "genre": _genre_from_text(lower),
        "protagonist": {
            "count": "one" if "one solitary" in lower or "solo" in lower or "one " in lower else "unspecified",
            "gender": _gender_from_text(lower),
            "description": _protagonist_description(lower),
            "wardrobe": _wardrobe_from_text(positive_text),
            "primary_action": _primary_action_from_text(positive_text),
        },
        "world": {
            "positive_description": _world_description(lower, positive_text),
            "motifs": motifs,
            "forbidden": _dedupe(forbidden),
        },
        "emotional_arc": _emotional_arc(lower),
        "style": {
            "look": "cinematic live-action",
            "avoid": ["collage", "duplicate subject", "text overlay"],
        },
    }


def adapt_acestep_audio_prompt(contract: dict, plan: dict | None = None) -> dict:
    plan = plan if isinstance(plan, dict) else {}
    world = contract.get("world", {}) if isinstance(contract, dict) else {}
    genre = _audio_genre_label(_first_nonempty(contract.get("genre") if isinstance(contract, dict) else "", plan.get("genre_head"), plan.get("tags")))
    vocal = _first_nonempty(plan.get("vocal_profile"), "intimate solo vocal")
    tone = _first_nonempty(plan.get("vocal_tone"), "warm restrained delivery")
    arc = contract.get("emotional_arc", []) if isinstance(contract.get("emotional_arc"), list) else []
    emotional = ", ".join(arc) if arc else "quiet tension to calm resolve"
    source = _first_nonempty(plan.get("genre_description"), plan.get("tags"), plan.get("audio_direction"), world.get("positive_description"))
    production = _audio_production_texture(source)
    tags = _join_audio_tags([genre, production, vocal, tone, emotional, "steady midtempo", "clean ending"])
    forbidden = list(world.get("forbidden", []))
    clean_tags = _budget_text(_strip_forbidden_words(_remove_negative_clauses(tags), forbidden), 500)
    return {
        "workflow": "acestep",
        "tags": clean_tags,
        "lyrics": str(plan.get("lyrics", "")).strip(),
        "negative_constraints": forbidden,
    }


def adapt_flux2_tti_anchor_prompt(contract: dict, anchor: dict | None = None) -> dict:
    world = contract.get("world", {}) if isinstance(contract, dict) else {}
    protagonist = contract.get("protagonist", {}) if isinstance(contract, dict) else {}
    gender = str(protagonist.get("gender", "unspecified")).strip() or "unspecified"
    presentation = "androgynous presentation" if gender == "unspecified" else f"{gender} presentation"
    prompt = _join_sentences(
        [
            f"Upper-body portrait of one solitary adult protagonist with {presentation} on a seamless pure white studio background.",
            f"Calm focused expression, natural face, clear face visibility, {_wardrobe_from_contract(contract)}.",
            "Neutral cinematic realism, soft studio light, clean identity card framing, prop-free plain studio setup, scenery-free composition, one person only.",
        ]
    )
    return {
        "workflow": "flux2_tti_anchor",
        "positive_text": _strip_forbidden_words(prompt, world.get("forbidden", [])),
        "negative_constraints": list(world.get("forbidden", [])),
    }


def adapt_flux2_ref_still_prompt(contract: dict, render_item: dict) -> dict:
    world = contract.get("world", {}) if isinstance(contract, dict) else {}
    story = render_item.get("story_contract") if isinstance(render_item, dict) and isinstance(render_item.get("story_contract"), dict) else {}
    action = _workflow_action_for_item(contract, render_item, still=True)
    final_payoff = _is_final_payoff_item(render_item)
    if final_payoff:
        action = _final_payoff_readable_action(world)
    alignment = _strip_default_world_leaks(
        _workflow_safe_alignment(_first_nonempty(story.get("section_alignment"), story.get("story_progression"), "quiet emotional progression")),
        contract,
    ).strip(" .")
    camera = _still_camera_for_item(render_item)
    shot_grammar = _strip_default_world_leaks(_workflow_safe_alignment(story.get("story_action_grammar", "")), contract).strip(" .")
    if final_payoff:
        shot_grammar = _final_payoff_staging(world)
    scene = _workflow_scene_description(world)
    prompt = _join_sentences(
        [
            "Use the reference character identity exactly.",
            f"A solitary protagonist in {scene}, {action}.",
            f"Scene continuity: {scene}, stable practical wardrobe silhouette, exact same shirt color and collar details from the reference image, one readable protagonist only.",
            f"{camera}, {alignment}.",
            f"Shot-specific staging: {shot_grammar}." if shot_grammar else "",
            "Single cinematic live-action still frame, one continuous scene, natural skin texture, clear readable subject.",
        ]
    )
    negatives = _dedupe([*world.get("forbidden", []), *_negative_constraints_from_text(_model_source_text(render_item))])
    return {
        "workflow": "flux2_ref_still",
        "positive_text": _budget_text(_strip_forbidden_words(_clean_model_sentence(prompt), negatives), 1200),
        "negative_constraints": negatives,
    }


def adapt_ltx_ia2v_prompt(contract: dict, render_item: dict, base_negative: str = "") -> dict:
    world = contract.get("world", {}) if isinstance(contract, dict) else {}
    story = render_item.get("story_contract") if isinstance(render_item, dict) and isinstance(render_item.get("story_contract"), dict) else {}
    action = _workflow_action_for_item(contract, render_item, still=False)
    final_payoff = _is_final_payoff_item(render_item)
    if final_payoff:
        action = _final_payoff_motion_action(world)
    action = _duration_safe_action(action, render_item.get("recommended_duration_sec"))
    camera = _clip_camera_for_item(render_item)
    shot_grammar = _strip_default_world_leaks(_workflow_safe_alignment(story.get("story_action_grammar", "")), contract).strip(" .")
    if final_payoff:
        shot_grammar = _final_payoff_motion_staging(world)
    scene = _workflow_scene_description(world)
    motion_cue = _world_motion_cue(world)
    prompt = _join_sentences(
        [
            f"scene: {scene}.",
            "character: same solo protagonist from the source still, stable practical wardrobe silhouette and clear face continuity.",
            f"action: {action}.",
            f"staging: {shot_grammar}." if shot_grammar else "",
            f"camera: {camera}, single continuous shot, {motion_cue}.",
        ]
    )
    source_text = _model_source_text(render_item)
    negatives = _dedupe(
        [
            *_split_negative_text(base_negative),
            *world.get("forbidden", []),
            *_negative_constraints_from_text(source_text),
            *(_final_payoff_motion_negatives() if final_payoff else []),
            *_DEFAULT_VISUAL_NEGATIVES,
        ]
    )
    positive = _remove_negative_clauses(_clean_model_sentence(prompt))
    positive = _strip_forbidden_words(positive, negatives)
    return {
        "workflow": "ltx_ia2v",
        "positive_text": _budget_text(positive, 900),
        "negative_text": ", ".join(negatives),
        "negative_constraints": negatives,
    }


def build_workflow_prompt_payloads(contract: dict, render_item: dict, *, base_ltx_negative: str = "") -> dict:
    return {
        "flux2_ref_still": adapt_flux2_ref_still_prompt(contract, render_item),
        "ltx_ia2v": adapt_ltx_ia2v_prompt(contract, render_item, base_negative=base_ltx_negative),
    }


def _audio_genre_label(text: object) -> str:
    lower = str(text or "").lower()
    if "alt-pop" in lower or "alt pop" in lower:
        return "Alt Pop"
    if "city pop" in lower or "citypop" in lower:
        return "City Pop"
    if "synthwave" in lower:
        return "Synthwave"
    if "k-pop" in lower or "kpop" in lower:
        return "K-Pop"
    if "k-indie" in lower or "k indie" in lower:
        return "K-Indie"
    if "j-rock" in lower or "j rock" in lower:
        return "J-Rock"
    if "dream-pop" in lower or "dream pop" in lower:
        return "Dream Pop"
    return "Pop"


def _audio_production_texture(text: object) -> str:
    lower = str(text or "").lower()
    parts: list[str] = []
    if "radio" in lower:
        parts.append("subtle radio-static percussion")
    if "desert" in lower or "sparse" in lower:
        parts.append("sparse warm analog textures")
    if "guitar" in lower:
        parts.append("muted electric guitar shimmer")
    if "synth" in lower or "analog" in lower:
        parts.append("warm analog synth pulse")
    if not parts:
        parts.append("warm analog pulse")
    return ", ".join(_dedupe(parts))


def _join_audio_tags(parts: Iterable[str]) -> str:
    return ", ".join(_dedupe([str(part).strip(" ,.") for part in parts if str(part).strip(" ,.")]))


def _genre_from_text(lower: str) -> str:
    if "alt-pop" in lower or "alt pop" in lower:
        return "alt-pop music video"
    if "synthwave" in lower:
        return "synthwave music video"
    if "k-indie" in lower or "k indie" in lower:
        return "k-indie music video"
    if "j-rock" in lower or "j rock" in lower:
        return "j-rock music video"
    if "dream-pop" in lower or "dream pop" in lower:
        return "dream-pop music video"
    if "city pop" in lower or "citypop" in lower:
        return "city pop music video"
    if "music video" in lower:
        return "music video"
    return ""


def _gender_from_text(lower: str) -> str:
    if re.search(r"\b(woman|female|girl|she|her)\b", lower):
        return "female"
    if re.search(r"\b(man|male|boy|he|him)\b", lower):
        return "male"
    return "unspecified"


def _protagonist_description(lower: str) -> str:
    if "solitary protagonist" in lower:
        return "solitary protagonist"
    if "protagonist" in lower:
        return "protagonist"
    return "lead performer"


def _world_description(lower: str, positive_text: str) -> str:
    if "desert" in lower and "radio" in lower:
        return "sunrise desert dunes with a distant radio tower and fading radio signal"
    if "arctic" in lower or "observatory" in lower or "aurora" in lower:
        return "arctic observatory, pulsing aurora signal, blue ice, snow-covered satellite dish"
    if "greenhouse" in lower:
        return "rainy greenhouse, fogged glass plants, flickering cassette recorder, soft morning rain"
    if "cliffside" in lower or "lighthouse" in lower:
        return "stormy cliffside lighthouse, black rocks, broken signal lantern, rotating lighthouse beam"
    if "underwater" in lower or "library" in lower:
        return "underwater library, floating books, pearl light, moonlit surface door"
    return positive_text


def _wardrobe_from_text(positive_text: str) -> str:
    lower = str(positive_text or "").lower()
    match = re.search(r"([^,.]+?silhouette)\b", positive_text, flags=re.I)
    if match:
        matched = _clean_model_sentence(match.group(1))
        if "desert" in lower and "radio" in lower and matched.lower() in {"stable wardrobe silhouette", "a stable wardrobe silhouette"}:
            return "stable wardrobe silhouette: light olive-gray desert travel overshirt, neutral shirt collar, dark trousers"
        return matched
    if "parka" in lower:
        return "stable silver parka silhouette"
    if "coat" in lower:
        return "stable coat silhouette"
    if "dress" in lower:
        return "stable dress silhouette"
    return "stable practical wardrobe silhouette"


def _wardrobe_from_contract(contract: dict) -> str:
    protagonist = contract.get("protagonist", {}) if isinstance(contract, dict) else {}
    wardrobe = str(protagonist.get("wardrobe", "")).strip() if isinstance(protagonist, dict) else ""
    return wardrobe or "stable practical wardrobe silhouette"


def _primary_action_from_text(positive_text: str) -> str:
    text = str(positive_text or "")
    patterns = (
        r"protagonist\s+([^,.]+)",
        r"solo adult protagonist\s+([^,.]+)",
        r"one male protagonist\s+([^,.]+)",
        r"one female protagonist\s+([^,.]+)",
    )
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.I)
        if match:
            return _clean_model_sentence(match.group(1))
    return ""


def _workflow_scene_description(world: dict) -> str:
    description = _first_nonempty(world.get("positive_description") if isinstance(world, dict) else "", "concept-specific music-video world")
    return _clean_model_sentence(description).strip(" .")


def _world_motion_cue(world: dict) -> str:
    description = str(world.get("positive_description", "") if isinstance(world, dict) else "").lower()
    if "desert" in description or "radio tower" in description:
        return "natural wind motion across clothing edges and drifting sand traces"
    if "arctic" in description or "observatory" in description or "aurora" in description:
        return "snow gusts, a soft aurora pulse, and subtle satellite-dish vibration"
    if "greenhouse" in description:
        return "rain streaks on glass, leaves trembling, and condensation sliding"
    if "lighthouse" in description or "cliffside" in description:
        return "storm spray, coat whip, and rotating lighthouse beam sweep"
    if "underwater" in description or "library" in description:
        return "floating fabric, drifting books, and soft light caustics"
    return "small environment motion matching the source still"


def _visible_fallback_action(contract: dict, render_item: dict, *, still: bool) -> str:
    world = contract.get("world", {}) if isinstance(contract, dict) and isinstance(contract.get("world"), dict) else {}
    description = str(world.get("positive_description", "")).lower()
    if "desert" in description or "radio tower" in description:
        return "pauses beside the silent radio, hand near the dial, then looks toward the distant tower"
    if "arctic" in description or "observatory" in description or "aurora" in description:
        return "steps across blue ice as the aurora pulse reflects across the face"
    if "greenhouse" in description:
        return "repairs the flickering cassette recorder beside fogged glass plants"
    if "lighthouse" in description or "cliffside" in description:
        return "carries the broken signal lantern up black rocks toward the rotating beam"
    if "underwater" in description or "library" in description:
        return "drifts through floating books and reaches toward the moonlit surface door"
    return "performs one readable hand turn or step that changes the scene composition"


def _workflow_action_for_item(contract: dict, render_item: dict, *, still: bool) -> str:
    world = contract.get("world", {}) if isinstance(contract, dict) else {}
    protagonist = contract.get("protagonist", {}) if isinstance(contract, dict) else {}
    primary = str(protagonist.get("primary_action", "")).strip() if isinstance(protagonist, dict) else ""
    story = render_item.get("story_contract") if isinstance(render_item, dict) and isinstance(render_item.get("story_contract"), dict) else {}
    candidates = [
        story.get("protagonist_action"),
        story.get("visual_event"),
        _extract_visual_action(render_item.get("still_prompt_text" if still else "clip_positive_prompt", "")),
        _extract_visual_action(render_item.get("prompt_seed" if still else "clip_prompt_seed", "")),
        primary,
    ]
    forbidden = list(world.get("forbidden", [])) if isinstance(world, dict) else []
    for candidate in candidates:
        action = _strip_forbidden_words(_strip_default_world_leaks(_workflow_safe_alignment(candidate), contract), forbidden).strip(" .")
        if action and not _looks_like_default_desert_radio_leak(action, contract):
            return action
    if primary:
        return _strip_forbidden_words(_strip_default_world_leaks(_workflow_safe_alignment(primary), contract), forbidden).strip(" .")
    return _visible_fallback_action(contract, render_item, still=still)


def _looks_like_default_desert_radio_leak(text: str, contract: dict) -> bool:
    lower = str(text or "").lower()
    source = _contract_positive_source(contract)
    leaked = ("desert", "dune", "radio", "tower", "sunrise")
    return any(term in lower and term not in source for term in leaked)


def _contract_positive_source(contract: dict) -> str:
    if not isinstance(contract, dict):
        return ""
    text = str(contract.get("positive_text", "")).lower()
    if text:
        return text
    world = contract.get("world", {}) if isinstance(contract.get("world"), dict) else {}
    return str(world.get("positive_description", "")).lower()


def _strip_default_world_leaks(text: str, contract: dict) -> str:
    value = str(text or "")
    source = _contract_positive_source(contract)
    if "radio" not in source:
        value = re.sub(r"\b(?:silent|dead|faint|fading)?\s*radio(?:\s+(?:wound|signal|tower|static|light|interference|voice))?\b", "", value, flags=re.I)
        value = re.sub(r"\bradio\s+\w+\b", "", value, flags=re.I)
    if "desert" not in source and "dune" not in source:
        value = re.sub(r"\b(?:sunrise\s+)?(?:desert|dune|dunes|sand|sandy)\b", "", value, flags=re.I)
    value = re.sub(r"\bsignal world\b", "", value, flags=re.I)
    return _finalize_prompt_text(value)


def _motifs_from_positive_text(lower: str) -> list[str]:
    motifs: list[str] = []
    if "radio tower" in lower:
        motifs.append("distant radio tower")
    if "radio" in lower or "signal" in lower:
        motifs.append("fading radio signal")
    if "sunrise" in lower:
        motifs.append("sunrise horizon")
    if "desert" in lower or "dune" in lower:
        motifs.append("desert dunes")
    return _dedupe(motifs)


def _emotional_arc(lower: str) -> list[str]:
    out: list[str] = []
    if "quiet uncertainty" in lower:
        out.append("quiet uncertainty")
    if "calm resolve" in lower:
        out.append("calm resolve")
    return out


def _forbidden_terms_from_clause(clause: str) -> list[str]:
    text = _NEGATIVE_PREFIX_RE.sub("", clause).strip()
    text = re.sub(r"\bor\b", ",", text, flags=re.I)
    text = re.sub(r"\band\b", ",", text, flags=re.I)
    return [part.strip(" .") for part in text.split(",") if part.strip(" .")]


def _model_source_text(render_item: dict) -> str:
    if not isinstance(render_item, dict):
        return ""
    return " ".join(str(render_item.get(key, "")) for key in ("prompt_seed", "prompt_draft", "still_prompt_text", "clip_prompt_seed", "clip_positive_prompt"))


def _extract_visual_action(text: object) -> str:
    raw = str(text or "")
    lowered = raw.lower()
    for label in ("protagonist action:", "story visual event:", "action:"):
        idx = lowered.find(label)
        if idx >= 0:
            segment = raw[idx + len(label):]
            return _clean_model_sentence(segment.split(",", 1)[0])
    for phrase in (
        "follow the first radio signal trace across the dunes",
        "raise the radio toward the distant tower",
        "turns toward the fading radio signal",
        "follows the fading signal",
    ):
        if phrase in lowered:
            return phrase
    return ""


def _is_final_payoff_item(render_item: dict) -> bool:
    if not isinstance(render_item, dict):
        return False
    anchor = str(render_item.get("selected_pose_anchor_id", "")).lower()
    story = render_item.get("story_contract") if isinstance(render_item.get("story_contract"), dict) else {}
    combined = " ".join(
        str(value or "")
        for value in (
            anchor,
            render_item.get("story_function"),
            render_item.get("section_type"),
            render_item.get("visual_mode"),
            story.get("visual_payoff"),
            story.get("story_function"),
        )
    ).lower()
    return "final_payoff" in anchor or "final payoff" in combined or "payoff" in combined and "resolved" in combined


def _final_payoff_readable_action(world: dict) -> str:
    description = str(world.get("positive_description", "") if isinstance(world, dict) else "").lower()
    if "desert" in description or "radio tower" in description:
        return "stands facing the viewer with the resolved radio signal held close to the body and calm resolve visible in the eyes"
    return "stands facing the viewer in a resolved still pose with calm emotion visible in the eyes"


def _final_payoff_staging(world: dict) -> str:
    description = str(world.get("positive_description", "") if isinstance(world, dict) else "").lower()
    if "desert" in description or "radio tower" in description:
        return "centered front-facing hold, bright sunrise light on the face, radio tower behind as a soft distant motif, eyes and upper wardrobe clearly readable"
    return "centered front-facing hold, bright key light on the face, eyes and upper wardrobe clearly readable"


def _final_payoff_motion_action(world: dict) -> str:
    description = str(world.get("positive_description", "") if isinstance(world, dict) else "").lower()
    if "desert" in description or "radio tower" in description:
        return "remain front-facing throughout while holding the resolved radio close, maintain direct viewer-facing gaze, minimal motion in the hands and shoulders"
    return "remain front-facing throughout in a resolved hold, maintain direct viewer-facing gaze, minimal motion in the hands and shoulders"


def _final_payoff_motion_staging(world: dict) -> str:
    description = str(world.get("positive_description", "") if isinstance(world, dict) else "").lower()
    if "desert" in description or "radio tower" in description:
        return "centered front-facing payoff hold, maintain direct viewer-facing gaze, keep the radio tower softly behind, keep face and upper wardrobe readable for the whole clip"
    return "centered front-facing payoff hold, maintain direct viewer-facing gaze, keep face and upper wardrobe readable for the whole clip"


def _final_payoff_motion_negatives() -> list[str]:
    return ["profile turn", "back view", "walking away", "turning away", "losing eye contact"]


def _still_camera_for_item(render_item: dict) -> str:
    anchor = str(render_item.get("selected_pose_anchor_id", "")).lower() if isinstance(render_item, dict) else ""
    role = str(render_item.get("candidate_role", "")).lower() if isinstance(render_item, dict) else ""
    if "hero_closeup" in anchor or "hero" in role:
        return "medium close-up with readable face and three-quarter camera angle"
    if "walking_side" in anchor:
        return "medium-wide three-quarter profile with readable face and clear body direction"
    if "final_payoff" in anchor:
        return "front-facing medium shot with bright front-lit readable face, direct viewer-facing gaze, calm resolved posture"
    return "medium-wide cinematic composition"


def _clip_camera_for_item(render_item: dict) -> str:
    role = str(render_item.get("candidate_role", "")).lower() if isinstance(render_item, dict) else ""
    if "world_bridge" in role:
        return "locked medium-wide shot with a gentle lateral drift"
    if "hero" in role:
        return "locked medium close-up with a subtle forward push"
    return "locked medium shot with gentle forward movement"


def _duration_safe_action(action: str, duration: object) -> str:
    clean = _clean_model_sentence(action).strip(" .")
    max_sec = 0.0
    if isinstance(duration, dict):
        try:
            max_sec = float(duration.get("max", 0.0) or 0.0)
        except Exception:
            max_sec = 0.0
    if max_sec and max_sec <= 2.0:
        return f"one clear micro-action: {clean}"
    return clean


def _negative_constraints_from_text(text: object) -> list[str]:
    raw = str(text or "")
    out: list[str] = []
    for match in _NEGATIVE_CLAUSE_RE.finditer(raw):
        term = _clean_negative_term(match.group(2))
        if term:
            out.append(term)
    return _dedupe(out)


def _clean_negative_term(text: str) -> str:
    value = _META_LABEL_RE.sub("", str(text or ""))
    value = value.split(";", 1)[0].strip(" .")
    value = re.sub(r"\s+", " ", value)
    lower = value.lower()
    if lower.startswith("duplicate subject"):
        return "duplicate subject"
    if lower.startswith("default to a static centered portrait"):
        return "default to a static centered portrait"
    if lower.startswith("repeating the same centered walking/performance pose"):
        return "repeating the same centered walking/performance pose"
    if lower.startswith("another centered hero performance hold"):
        return "another centered hero performance hold"
    if lower.startswith("hero performance hold"):
        return "hero performance hold"
    return value


def _workflow_safe_alignment(text: object) -> str:
    value = _remove_negative_clauses(_clean_model_sentence(text)).strip(" ,.")
    return value


def _split_negative_text(text: str) -> list[str]:
    return [part.strip(" .") for part in str(text or "").split(",") if part.strip(" .")]


def _remove_negative_clauses(text: str) -> str:
    cleaned = _NEGATIVE_CLAUSE_RE.sub("", text)
    return _finalize_prompt_text(cleaned)


def _clean_model_sentence(text: object) -> str:
    value = _META_LABEL_RE.sub("", str(text or ""))
    value = value.replace("role diversity world bridge", "environment-led desert bridge shot")
    value = value.replace("role diversity symbolic insert", "readable desert-radio cutaway detail")
    value = value.replace("beat-responsive camera motion", "gentle camera movement on the beat")
    value = value.replace("audio-reactive hook energy", "clear hook-section movement")
    value = value.replace("hook energy", "hook-section movement")
    value = value.replace("radio wound setup beat", "silent-radio setup beat")
    value = value.replace("starting wound", "starting hesitation")
    value = value.replace("night-world wound", "night-world hesitation")
    value = value.replace("concept-specific visual motif", "readable scene motif")
    value = value.replace("neon_highway", "long luminous path through the scene")
    value = value.replace("crosswalk_wait", "paused between wet plant rows beside fogged glass")
    value = value.replace("live_house_entry", "narrow threshold cut by performance light")
    value = value.replace("amp_corridor", "narrow path cut by rotating beam light")
    value = value.replace("window_haze", "pearl-lit haze through drifting book pages")
    value = value.replace("same block", "same desert space")
    value = value.replace("new angle", "changed camera angle")
    value = value.replace("evolved staging", "changed staging")
    value = re.sub(r"\s+", " ", value).strip(" ,.")
    value = re.sub(r"\.{2,}", ".", value)
    return value


def _finalize_prompt_text(text: str) -> str:
    value = re.sub(r"\s+", " ", str(text or "")).strip(" ,.")
    value = re.sub(r"\bnot a\s*([.,]|$)", "", value, flags=re.I)
    value = re.sub(r"\.{2,}", ".", value)
    value = re.sub(r"\s+,", ",", value)
    value = re.sub(r",\s*,", ",", value)
    value = value.strip(" ,.;")
    return f"{value}." if value else ""


def _strip_forbidden_words(text: str, forbidden: Iterable[str]) -> str:
    value = str(text or "")
    for term in forbidden:
        token = str(term or "").strip()
        if not token:
            continue
        value = re.sub(rf"\b{re.escape(token)}\b", "", value, flags=re.I)
    return _finalize_prompt_text(value)


def _budget_text(text: str, limit: int) -> str:
    clean = re.sub(r"\s+", " ", str(text or "")).strip()
    if len(clean) <= limit:
        return clean
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", clean) if part.strip()]
    out: list[str] = []
    for sentence in sentences:
        candidate = " ".join([*out, sentence]).strip()
        if len(candidate) > limit:
            break
        out.append(sentence)
    if out:
        return " ".join(out)
    return clean[:limit].rsplit(" ", 1)[0].strip(" ,.") + "."


def _join_sentences(parts: list[str]) -> str:
    out: list[str] = []
    for part in parts:
        value = str(part or "").strip()
        if value and value not in out:
            out.append(value)
    return " ".join(out)


def _first_nonempty(*values: object) -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return ""


def _dedupe(values: Iterable[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value or "").strip(" .,;")
        lower = text.lower()
        if text and lower not in seen:
            out.append(text)
            seen.add(lower)
    return out
