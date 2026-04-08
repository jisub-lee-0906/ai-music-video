from __future__ import annotations

from ai_mv.core.director_brief import build_director_brief_intent


def verbalize_ref_prompts(config: dict, rows: list[dict]) -> dict[str, str]:
    if not rows:
        return {}
    brief = build_director_brief_intent(config) if isinstance(config, dict) and config else {}
    out: dict[str, str] = {}
    previous: dict | None = None
    for row in rows:
        shot_id = str(row.get("shot_id", "")).strip()
        if not shot_id:
            continue
        out[shot_id] = _build_ref_prompt(brief, row, previous)
        previous = row
    return out


def verbalize_wan_prompts(config: dict, rows: list[dict]) -> dict[str, str]:
    if not rows:
        return {}
    brief = build_director_brief_intent(config) if isinstance(config, dict) and config else {}
    out: dict[str, str] = {}
    for row in rows:
        shot_id = str(row.get("shot_id", "")).strip()
        if not shot_id:
            continue
        out[shot_id] = _build_wan_prompt(brief, row)
    return out


def _build_ref_prompt(brief: dict, row: dict, previous: dict | None) -> str:
    subject = _subject_phrase(brief)
    place = _clean(row.get("place", ""))
    action = _clean(row.get("action", ""))
    carry = _clean(row.get("carry", ""))
    framing = _clean(row.get("framing", ""))
    literal_image = _clean(row.get("literal_image", ""))
    sentences: list[str] = []
    lead = _lead_sentence(subject, action, place, framing)
    if lead:
        sentences.append(lead)
    detail_sentence = _detail_sentence(literal_image)
    if detail_sentence:
        sentences.append(detail_sentence)
    carry_sentence = _carry_sentence(carry, previous)
    if carry_sentence:
        sentences.append(carry_sentence)
    finish = _cinematic_finish(brief, place, str(row.get("section_label", "")).strip())
    if finish:
        sentences.append(finish)
    sentences.append(_face_lock(brief))
    return " ".join(sentence for sentence in sentences if sentence).strip()


def _build_wan_prompt(brief: dict, row: dict) -> str:
    subject = _subject_phrase(brief)
    be = _be_verb(subject)
    remain = _remain_verb(subject)
    place = _clean(row.get("place", ""))
    action = _clean(row.get("bridge_action", ""))
    carry = _clean(row.get("carry", ""))
    pieces = [
        _sentence(
            f"{subject} {be} {action}{_place_tail(place)}"
            if action
            else f"{subject} {remain}{_place_tail(place)}"
            if place
            else f"{subject} keeps moving forward"
        ),
        _carry_sentence(carry, None, prefix="The same "),
        _cinematic_finish(brief, place, str(row.get("section_label", "")).strip()),
    ]
    return " ".join(piece for piece in pieces if piece).strip()


def _lead_sentence(subject: str, action: str, place: str, framing: str) -> str:
    be = _be_verb(subject)
    remain = _remain_verb(subject)
    if not action and not place:
        return ""
    if action and place:
        return _sentence(_lead_clause(subject, be, action, place, framing))
    if action:
        tail = f", {framing}" if framing else ""
        return _sentence(f"{subject} {be} {action}{tail}")
    tail = f", {framing}" if framing else ""
    return _sentence(f"{subject} {remain}{_place_tail(place)}{tail}")


def _place_tail(place: str) -> str:
    lowered = place.lower()
    if lowered.startswith(("in ", "at ", "by ", "along ", "inside ", "outside ", "near ")):
        return f" {place}"
    if lowered.startswith(("a ", "an ", "the ")):
        core = place
    else:
        core = f"a {place}"
    if any(token in lowered for token in ("street", "crosswalk", "intersection", "road", "sidewalk")):
        return f" on {core}"
    if any(token in lowered for token in ("rooftop", "elevated deck")):
        return f" on {core}"
    return f" in {core}"


def _carry_sentence(carry: str, previous: dict | None, prefix: str = "") -> str:
    if not carry:
        return ""
    if isinstance(previous, dict) and _clean(previous.get("carry", "")) == carry:
        return ""
    lowered = carry.lower()
    subject = carry if lowered.startswith(("the ", "a ", "an ")) else f"the {carry}"
    if prefix and subject.lower().startswith("the "):
        subject = subject[4:]
    verb = "stay" if prefix else "remain"
    text = f"{prefix}{subject} {verb} in view".strip()
    return _sentence(_capitalize(text))


def _detail_sentence(literal_image: str) -> str:
    if not literal_image:
        return ""
    return _sentence(_literal_clause(literal_image))




def _cinematic_finish(brief: dict, place: str, section_label: str) -> str:
    genre = str(brief.get("profile_genre", "")).lower()
    low_place = place.lower()
    low_section = section_label.lower()
    if any(token in low_place for token in ("street", "sidewalk", "crosswalk", "intersection", "road")):
        lens = "anamorphic lens"
        lighting = "natural streetlight contrast"
    elif any(token in low_place for token in ("diner", "cafe", "room", "club", "stairwell", "interior")):
        lens = "35mm photography"
        lighting = "soft practical lighting"
    else:
        lens = "cinematic lensing"
        lighting = "natural cinematic lighting"
    texture = "subtle film grain" if any(token in genre for token in ("pop", "synth")) else "film grain"
    dof = "controlled depth of field" if "chorus" in low_section else "shallow depth of field"
    return _sentence(f"{_capitalize(lighting)}, {texture}, {dof}, {lens}")


def _lead_clause(subject: str, be: str, action: str, place: str, framing: str) -> str:
    tail = f", {framing}" if framing else ""
    if " and " in action:
        first, second = action.split(" and ", 1)
        return f"{subject} {be} {first}{_place_tail(place)}, {second}{tail}"
    return f"{subject} {be} {action}{_place_tail(place)}{tail}"


def _subject_phrase(brief: dict) -> str:
    voice = str(brief.get("profile_voice", "")).lower()
    if "duo" in voice or "group" in voice or "mixed" in voice:
        return "They"
    if "female" in voice or "woman" in voice or "girl" in voice:
        return "She"
    if "male" in voice or "man" in voice or "boy" in voice:
        return "He"
    return "The performer"


def _face_lock(brief: dict) -> str:
    voice = str(brief.get("profile_voice", "")).lower()
    if "duo" in voice or "group" in voice or "mixed" in voice:
        return "Keep the faces consistent."
    return "Keep the face."


def _be_verb(subject: str) -> str:
    lowered = subject.lower()
    return "are" if lowered == "they" or subject.endswith("s") else "is"


def _remain_verb(subject: str) -> str:
    lowered = subject.lower()
    return "remain" if lowered == "they" or subject.endswith("s") else "remains"


def _literal_clause(text: str) -> str:
    cleaned = _clean(text)
    lowered = cleaned.lower()
    if lowered.startswith(("a ", "an ", "the ")):
        return _capitalize(cleaned)
    return _capitalize(cleaned)


def _sentence(text: str) -> str:
    cleaned = _clean(text)
    return f"{cleaned}." if cleaned else ""


def _clean(text: object) -> str:
    return " ".join(str(text).strip().rstrip(". ").split())


def _capitalize(text: str) -> str:
    cleaned = _clean(text)
    if not cleaned:
        return ""
    return cleaned[0].upper() + cleaned[1:]


def _looks_like_english_clause(text: str) -> bool:
    words = [w for w in _clean(text).lower().split() if w]
    alpha_words = sum(1 for w in words if any("a" <= ch <= "z" for ch in w))
    return alpha_words >= max(2, len(words) // 2 or 1)
