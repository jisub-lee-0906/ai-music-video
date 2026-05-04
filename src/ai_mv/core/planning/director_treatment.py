from __future__ import annotations


def build_director_treatment(*, concept_text: str, style_name: str, sections: list[dict]) -> dict:
    text = str(concept_text or "").strip()
    normalized_style = str(style_name or "").strip()
    story_beats = [_build_story_beat(idx, section, total=len(sections), text=text) for idx, section in enumerate(sections, start=1)]
    return {
        "story_logline": _story_logline(text=text, style_name=normalized_style),
        "protagonist_arc": _protagonist_arc(text=text),
        "story_beats": story_beats,
        "motif_arc": _motif_arc(text=text, style_name=normalized_style),
        "anti_repetition_rules": _anti_repetition_rules(),
        "style_lane": normalized_style,
        "section_count": len(sections),
    }


def _story_logline(*, text: str, style_name: str) -> str:
    if any(token in text.lower() for token in ("goodbye", "missed train", "resolve", "이별", "전철")):
        return "A lone night-city protagonist follows the traces of an unfinished goodbye and chooses forward motion by the final image."
    if style_name == "idol_pop":
        return "A lead performer turns a city-night performance world from introduction into confident hook release and afterglow."
    return "A lone protagonist moves through one coherent music-video world from setup toward a visible emotional release."


def _protagonist_arc(*, text: str) -> dict:
    lower = text.lower()
    if any(token in lower for token in ("goodbye", "missed train", "resolve", "이별", "전철")):
        return {
            "start_state": "waiting and haunted by an unfinished goodbye",
            "desire": "to recover or answer the lost connection",
            "obstacle_or_wound": "the city keeps reflecting the moment they failed to leave behind",
            "turning_point": "the hook turns waiting into forward motion",
            "end_state": "quiet resolve, no longer defined by waiting",
        }
    return {
        "start_state": "contained and searching",
        "desire": "to turn the song world into a clear emotional release",
        "obstacle_or_wound": "the visual world can collapse into mood without decision",
        "turning_point": "the chorus makes the emotional change visible",
        "end_state": "resolved into a final afterimage with clearer intent",
    }


def _build_story_beat(idx: int, section: dict, *, total: int, text: str) -> dict:
    section_type = str(section.get("section_type", "")).strip().lower()
    section_name = str(section.get("section_name", "")).strip()
    is_last = idx == total
    story_function = _story_function(section_type, is_last=is_last, idx=idx)
    return {
        "beat_id": f"B{idx:03d}",
        "section_id": str(section.get("section_id", "")).strip(),
        "section_name": section_name,
        "section_role": section_type,
        "story_function": story_function,
        "visual_event": _visual_event(story_function=story_function, text=text),
        "emotional_state": _emotional_state(story_function),
        "required_change_from_previous": _required_change(story_function),
        "payoff_requirement": _payoff_requirement(story_function),
    }


def _story_function(section_type: str, *, is_last: bool, idx: int) -> str:
    if is_last or section_type == "outro":
        return "payoff"
    if idx == 1 or section_type == "intro":
        return "wound_setup"
    if section_type == "chorus":
        return "release"
    if section_type in {"pre_chorus", "bridge"}:
        return "threshold"
    return "search"


def _visual_event(*, story_function: str, text: str) -> str:
    lower = _positive_text(text)
    night_city = any(token in lower for token in ("neon", "night", "city", "wet", "train", "전철"))
    desert_radio = any(token in lower for token in ("desert", "dune", "sand")) and any(
        token in lower for token in ("radio", "signal", "tower", "antenna")
    )
    if story_function == "wound_setup" and desert_radio:
        return "establish the protagonist isolated with a silent radio in the desert signal world"
    if story_function == "search" and desert_radio:
        return "follow the first radio signal trace across the dunes instead of repeating the opener pose"
    if story_function == "threshold" and desert_radio:
        return "tighten around the radio direction cue before the signal becomes unavoidable"
    if story_function == "release" and desert_radio:
        return "make the hook visibly larger through radio static, sunrise light, and a stronger decision pose"
    if story_function == "payoff" and desert_radio:
        return "show the radio signal resolved or released against the sunrise horizon"
    if story_function == "wound_setup":
        return "establish the protagonist isolated inside the night-world wound"
    if story_function == "search":
        return "follow traces through the world instead of repeating the opener pose"
    if story_function == "threshold":
        return "tighten around a visible decision point before the hook lift"
    if story_function == "release":
        return "make the hook visibly larger through action, light, or performance turn"
    if story_function == "payoff" and night_city:
        return "show a final decision toward dawn or forward motion rather than another waiting pose"
    return "show a final decision that resolves the protagonist arc"


def _emotional_state(story_function: str) -> str:
    return {
        "wound_setup": "stuck",
        "search": "pulled_backward",
        "threshold": "almost_choosing",
        "release": "release",
        "payoff": "resolve",
    }.get(story_function, "progressing")


def _required_change(story_function: str) -> str:
    return {
        "wound_setup": "establish the baseline without solving the arc",
        "search": "change location function or action beat from the opener",
        "threshold": "increase tension with a more specific decision cue",
        "release": "increase energy and change at least one of action, framing, or light intensity",
        "payoff": "change at least two of camera distance, action, emotional state, or location function from the prior shot",
    }.get(story_function, "advance the story function")


def _payoff_requirement(story_function: str) -> str:
    if story_function == "release":
        return "the hook must read as a visible emotional turn, not only the same mood at higher brightness"
    if story_function == "payoff":
        return "the final image must show a decision or changed state through face, action, gesture, or forward motion"
    return ""


def _motif_arc(*, text: str, style_name: str) -> dict:
    lower = _positive_text(text)
    motifs: dict[str, str] = {}
    if any(token in lower for token in ("desert", "dune", "sand")) and any(
        token in lower for token in ("radio", "signal", "tower", "antenna")
    ):
        motifs["radio_signal"] = "silent radio -> faint signal -> static confrontation -> released silence"
        motifs["desert_sunrise"] = "pre-dawn dunes -> signal path -> sunrise horizon payoff"
    if any(token in lower for token in ("rain", "wet", "neon", "city")) or style_name in {"citypop", "synthwave"}:
        motifs["rain_reflection"] = "distorted memory -> active movement -> clearer final reflection"
        motifs["city_light"] = "background mood -> decision pressure -> release path"
    if any(token in lower for token in ("train", "station", "전철")):
        motifs["station_light"] = "missed timing -> threshold cue -> departure energy"
    if not motifs:
        motifs["signature_object"] = "setup symbol -> tension cue -> payoff echo"
    return motifs


def _anti_repetition_rules() -> list[str]:
    return [
        "Do not repeat centered lonely wide walking shots as the only emotional language.",
        "Chorus and payoff beats must change at least one visible dimension from verse support shots.",
        "Final shot must show a decision, not just mood.",
        "If a beat is marked payoff, avoid another generic static neon-street pose unless it visibly resolves the arc.",
    ]


def _positive_text(text: object) -> str:
    pieces: list[str] = []
    for raw_part in str(text or "").lower().split(","):
        part = raw_part.strip()
        if not part:
            continue
        if part.startswith(("no ", "without ", "avoid ", "never ")):
            continue
        pieces.append(part)
    return ", ".join(pieces)
