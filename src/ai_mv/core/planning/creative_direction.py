from __future__ import annotations


def build_creative_direction(*, concept_text: str, style_name: str, sections: list[dict], continuity_mode: str = "strict") -> dict:
    text = str(concept_text or "").strip().lower()
    section_types = [str(row.get("section_type", "")).strip() for row in sections if isinstance(row, dict)]
    if any(name == "chorus" for name in section_types):
        mv_mode = "visualizer"
    else:
        mv_mode = "hybrid"
    hook_visual = _hook_visual(text=text, style_name=style_name)
    emotional_arc = _emotional_arc(text=text)
    normalized_continuity_mode = _normalize_continuity_mode(continuity_mode)
    return {
        "mv_mode": mv_mode,
        "hook_visual": hook_visual,
        "emotional_arc": emotional_arc,
        "visual_rules": _visual_rules(style_name=style_name),
        "chorus_intent": _chorus_intent(text=text),
        "bridge_intent": _bridge_intent(text=text),
        "continuity_mode": normalized_continuity_mode,
        "continuity_rules": _continuity_rules(style_name=style_name, continuity_mode=normalized_continuity_mode),
        "style_lane": str(style_name).strip(),
        "section_count": len(sections),
    }


def _hook_visual(*, text: str, style_name: str) -> str:
    if "night drive" in text:
        return "night drive through neon-lit streets with reflective motion"
    if "romance" in text:
        return "lonely romantic close-ups against city light reflections"
    if style_name == "synthwave":
        return "retro neon boulevard imagery with glowing night geometry"
    return "a concept-led hero image that defines the MV world quickly"


def _emotional_arc(*, text: str) -> str:
    if "lonely" in text or "romance" in text:
        return "starts introspective, opens emotionally in the chorus, and fades with afterglow"
    return "builds from setup to release and closes on a clear final afterimage"


def _visual_rules(*, style_name: str) -> list[str]:
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


def _continuity_rules(*, style_name: str, continuity_mode: str) -> list[str]:
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
    if style_name == "synthwave":
        return [*base, "keep neon palette and reflective night setting stable across the sequence"]
    return base



def _normalize_continuity_mode(value: str) -> str:
    mode = str(value or "").strip().lower()
    if mode in {"strict", "moderate", "expressive"}:
        return mode
    return "strict"
