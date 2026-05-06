from __future__ import annotations


def build_creative_direction(*, concept_text: str, style_name: str, sections: list[dict], continuity_mode: str = "strict") -> dict:
    text = str(concept_text or "").strip().lower()
    positive_text = _positive_concept_text(text)
    section_types = [str(row.get("section_type", "")).strip() for row in sections if isinstance(row, dict)]
    if any(name == "chorus" for name in section_types):
        mv_mode = "visualizer"
    else:
        mv_mode = "hybrid"
    has_concept_world = bool(_concept_world_anchor(positive_text))
    hook_visual = _hook_visual(text=positive_text, style_name=style_name, has_concept_world=has_concept_world)
    emotional_arc = _emotional_arc(text=positive_text)
    normalized_continuity_mode = _normalize_continuity_mode(continuity_mode)
    return {
        "mv_mode": mv_mode,
        "hook_visual": hook_visual,
        "emotional_arc": emotional_arc,
        "visual_rules": _visual_rules(style_name=style_name, has_concept_world=has_concept_world),
        "chorus_intent": _chorus_intent(text=text),
        "bridge_intent": _bridge_intent(text=text),
        "continuity_mode": normalized_continuity_mode,
        "continuity_rules": _continuity_rules(style_name=style_name, continuity_mode=normalized_continuity_mode, has_concept_world=has_concept_world),
        "protagonist_anchor": _protagonist_anchor(text=positive_text, style_name=style_name, has_concept_world=has_concept_world),
        "world_anchor": _world_anchor(text=positive_text, style_name=style_name),
        "wardrobe_anchor": _wardrobe_anchor(text=positive_text, style_name=style_name, has_concept_world=has_concept_world),
        "style_lane": str(style_name).strip(),
        "section_count": len(sections),
    }


def _hook_visual(*, text: str, style_name: str, has_concept_world: bool = False) -> str:
    if has_concept_world:
        return "concept-world hero image with source-bound framing and readable protagonist action"
    if style_name == "idol_pop":
        return "bright front-facing performance moments against a glossy city-night stage world"
    if "night drive" in text:
        return "night drive through neon-lit streets with reflective motion"
    if "romance" in text:
        return "lonely romantic close-ups against city light reflections"
    if style_name == "synthwave":
        return "retro neon boulevard imagery with glowing night geometry"
    return "a concept-led hero image that defines the MV world quickly"


def _emotional_arc(*, text: str) -> str:
    if "lonely" in text or "romance" in text:
        return "starts introspective, opens emotionally in the chorus, and closes with source-bound release light"
    return "builds from setup to release and closes on a clear final afterimage"


def _visual_rules(*, style_name: str, has_concept_world: bool = False) -> list[str]:
    if style_name == "idol_pop":
        if has_concept_world:
            return [
                "preserve one coherent source-bound performance world",
                "favor bright readable faces and performance-capable framing",
                "avoid moody solitary drift or overly dark wardrobe collapse",
            ]
        return [
            "preserve one coherent glossy performance-night world",
            "favor bright readable faces and stage-ready performance framing",
            "avoid moody solitary drift or overly dark wardrobe collapse",
        ]
    if style_name == "synthwave":
        return [
            "preserve one coherent neon-night world",
            "favor reflective geometry and readable silhouettes",
            "avoid collage-like composition drift",
        ]
    return [
        "preserve one coherent visual world",
        "favor readable single-scene compositions",
        "avoid panelized or collage-like layout drift",
    ]


def _chorus_intent(*, text: str) -> str:
    if "night drive" in text:
        return "make the chorus feel larger and more open without losing the established world"
    return "increase visual lift and memorability in the chorus while preserving continuity"


def _bridge_intent(*, text: str) -> str:
    if "lonely" in text:
        return "use the bridge to turn inward before returning to the main release"
    return "use the bridge as a contrast beat before the final payoff"


def _protagonist_anchor(*, text: str, style_name: str, has_concept_world: bool = False) -> str:
    if _explicit_wardrobe_from_text(text):
        return "same lone protagonist, stable user-specified wardrobe, camera-readable face, no competing bystanders"
    if style_name == "idol_pop":
        if has_concept_world:
            return "same lead idol performer, stable bright performance outfit silhouette, camera-readable face, no competing co-stars"
        return "same lead idol performer, stable bright stage outfit silhouette, camera-readable face, no competing co-stars"
    if style_name == "synthwave":
        return "same lone synthwave protagonist, stable story-derived outfit silhouette, no competing bystanders"
    if any(token in text for token in ("walk", "wet", "neon", "late-night")):
        return "same lone night-walk protagonist, stable story-derived outfit silhouette, no competing bystanders"
    return "same lone protagonist, stable silhouette, no competing bystanders"


def _wardrobe_anchor(*, text: str, style_name: str, has_concept_world: bool = False) -> str:
    explicit = _explicit_wardrobe_from_text(text)
    if explicit:
        return explicit
    if style_name == "idol_pop":
        if has_concept_world:
            return "stable bright performance outfit silhouette"
        return "stable bright stage outfit silhouette"
    return "story-derived stable outfit silhouette"


def _world_anchor(*, text: str, style_name: str) -> str:
    concept_world = _concept_world_anchor(text)
    if concept_world:
        return concept_world
    if style_name == "idol_pop":
        return "same glossy city-night performance world, bright reflected lights, polished urban stage energy"
    if style_name == "synthwave":
        return "same neon-night boulevard world, reflective pavement, glowing urban signage"
    if any(token in text for token in ("wet", "neon", "city", "late-night")):
        return "same rain-slick neon boulevard world, wet asphalt reflections, dense urban signage"
    return "same coherent style world, readable scene depth, stable concept lighting"



def _concept_world_anchor(text: str) -> str:
    motifs: list[str] = []
    if any(token in text for token in ("desert", "dune", "sand")):
        motifs.append("same desert dune world")
    if any(token in text for token in ("greenhouse", "glasshouse", "seedling", "seedlings")):
        motifs.append("same greenhouse glasshouse world")
    if any(token in text for token in ("forest", "mossy", "moss", "pier")):
        motifs.append("same forest pier world")
    if any(token in text for token in ("underwater", "aquarium", "glass tunnel")):
        motifs.append("same underwater aquarium world")
    if any(token in text for token in ("arctic", "ice", "snow")):
        motifs.append("same arctic ice world")
    if any(token in text for token in ("meadow", "grass", "kites")):
        motifs.append("same spring meadow world")
    if any(token in text for token in ("lighthouse", "cliff", "coast")):
        motifs.append("same lighthouse cliff world")
    has_tower_source = any(token in text for token in ("tower", "antenna"))
    has_signal_source = "signal" in text
    has_radio_source = "radio" in text
    if has_tower_source and (has_radio_source or has_signal_source):
        motifs.append("distant radio tower direction")
    elif has_tower_source:
        motifs.append("distant tower motif")
    elif has_signal_source:
        motifs.append("source-bound direction cue")
    elif has_radio_source:
        motifs.append("radio object motif")
    if any(token in text for token in ("sunrise", "dawn")):
        motifs.append("sunrise horizon light")
    if motifs:
        return ", ".join(dict.fromkeys(motifs)) + ", avoid urban or street-location substitution"
    return ""



def _continuity_rules(*, style_name: str, continuity_mode: str, has_concept_world: bool = False) -> list[str]:
    mode = _normalize_continuity_mode(continuity_mode)
    if mode == "expressive":
        base = [
            "preserve emotional and palette continuity more than exact shot-to-shot identity locking",
            "allow intentional visual resets when the section turn benefits from contrast",
            "favor motion-safe source images over decorative complexity",
        ]
    elif mode == "moderate":
        base = [
            "keep protagonist and world continuity across nearby shots without over-locking every frame",
            "allow controlled variation in staging and location treatment inside one MV world",
            "favor motion-safe source images over decorative complexity",
        ]
    else:
        base = [
            "keep one protagonist identity across adjacent shots",
            "preserve world continuity between stills and clips",
            "favor motion-safe source images over decorative complexity",
        ]
    if style_name == "idol_pop":
        if has_concept_world:
            return [*base, "keep bright performance energy and readable face framing inside the source-bound concept world"]
        return [*base, "keep bright stage energy, readable face framing, and polished city-night gloss stable across the sequence"]
    if style_name == "synthwave":
        if has_concept_world:
            return [*base, "keep synthwave palette texture stable without replacing the source-bound concept world"]
        return [*base, "keep neon palette and reflective night setting stable across the sequence"]
    return base



def _normalize_continuity_mode(value: str) -> str:
    mode = str(value or "").strip().lower()
    if mode in {"strict", "moderate", "expressive"}:
        return mode
    return "strict"



def _positive_concept_text(text: str) -> str:
    """Drop comma-separated negative constraints before positive motif detection."""

    pieces: list[str] = []
    for raw_part in str(text or "").split(","):
        part = raw_part.strip()
        if not part:
            continue
        if part.startswith(("no ", "without ", "avoid ", "never ")):
            continue
        pieces.append(part)
    return ", ".join(pieces)


def _explicit_wardrobe_from_text(text: str) -> str:
    import re

    value = str(text or "")
    patterns = (
        r"\bin\s+(?:a|an|the)?\s*([^,.]{2,80}?\b(?:dress|coat|raincoat|parka|jacket|windbreaker|apron|scarf|hoodie|shirt|overshirt|suit))\b",
        r"\bwear(?:s|ing)?\s+(?:a|an|the)?\s*([^,.]{2,80}?\b(?:dress|coat|raincoat|parka|jacket|windbreaker|apron|scarf|hoodie|shirt|overshirt|suit))\b",
    )
    for pattern in patterns:
        match = re.search(pattern, value, flags=re.I)
        if match:
            return " ".join(match.group(1).split()).strip(" .")
    return ""
