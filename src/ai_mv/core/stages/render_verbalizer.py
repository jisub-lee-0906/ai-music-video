from __future__ import annotations

from ai_mv.core.director_brief import build_director_brief_intent
from ai_mv.core.prompt_grammar import load_flux2_prompting, load_render_verbalizer_rules
from ai_mv.infra.codex_cli_client import generate_structured, ping_codex


def verbalize_ref_prompt_pairs(config: dict, rows: list[dict]) -> dict[str, dict]:
    if not rows:
        return {}
    out: dict[str, dict] = {}
    previous: dict | None = None
    for row in rows:
        shot_id = str(row.get("shot_id", "")).strip()
        if not shot_id:
            continue
        start_prompt = _build_ref_prompt(config, row, previous, phase="start")
        end_prompt = _build_ref_prompt(config, row, previous, phase="end")
        out[shot_id] = {
            "start_prompt_text": start_prompt,
            "end_prompt_text": end_prompt,
        }
        previous = row
    return out


def verbalize_wan_prompts(config: dict, rows: list[dict]) -> dict[str, str]:
    if not rows:
        return {}
    try:
        if ping_codex(config):
            return _verbalize_wan_prompts_with_codex(config, rows)
    except Exception:
        pass
    out: dict[str, str] = {}
    for row in rows:
        shot_id = str(row.get("shot_id", "")).strip()
        if not shot_id:
            continue
        out[shot_id] = _join_prompt_parts(
            row.get("subject_intro", ""),
            row.get("location", ""),
            row.get("bridge_action", ""),
            row.get("story_event", ""),
            row.get("lighting", ""),
        )
    return out


def _build_ref_prompt(config: dict, row: dict, previous: dict | None, phase: str) -> str:
    brief = build_director_brief_intent(config) if isinstance(config, dict) and config else {}
    subject = _ref_subject(row, brief)
    action = _action_clause(row, phase)
    place = _place_clause(row, previous)
    support_parts = _support_parts(row, previous, phase)
    finish = _cinematic_finish(brief, row)
    sentences: list[str] = []
    lead = _lead_sentence(subject, action, place)
    if lead:
        sentences.append(lead)
    if place and (place.startswith("The same ") or place.startswith("The scene ")):
        sentences.append(_sentence(place))
    sentences.extend(_sentence(part) for part in support_parts if _clean_phrase(part))
    if finish:
        sentences.append(finish)
    sentences.append("Keep the face.")
    return " ".join(sentence for sentence in sentences if sentence).strip()


def _verbalize_ref_prompt_pairs_with_codex(config: dict, rows: list[dict]) -> dict[str, dict]:
    flux_rules = load_flux2_prompting().get("ref", {})
    flux_rule_block = _rule_block(
        flux_rules,
        "natural_language_contract",
        "preservation_bias",
        "hierarchy",
        "emphasis",
        "suppression",
    )
    schema = {
        "type": "object",
        "properties": {
            "shots": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "shot_id": {"type": "string"},
                        "start_prompt_text": {"type": "string"},
                        "end_prompt_text": {"type": "string"},
                    },
                    "required": ["shot_id", "start_prompt_text", "end_prompt_text"],
                },
            }
        },
        "required": ["shots"],
    }
    prompt = (
        "You are a render verbalizer for a music-video pipeline. "
        "Your job is only to merge already-decided prompt clauses into natural English prose for Flux image generation. "
        "Preserve meaning exactly. Do not add any new person, place, prop, action, relationship, emotion, symbolism, or story information. "
        f"{flux_rule_block} "
        f"{_instruction_block('ref_instruction_lines')} "
        "Return JSON only.\n\n"
        f"Shots={rows}"
    )
    raw = generate_structured(config, prompt, schema, attempts=1)
    out: dict[str, dict] = {}
    for row in raw.get("shots", []):
        if not isinstance(row, dict):
            continue
        shot_id = str(row.get("shot_id", "")).strip()
        start = " ".join(str(row.get("start_prompt_text", "")).strip().split())
        end = " ".join(str(row.get("end_prompt_text", "")).strip().split())
        if shot_id and start and end:
            out[shot_id] = {"start_prompt_text": start, "end_prompt_text": end}
    return out


def _verbalize_wan_prompts_with_codex(config: dict, rows: list[dict]) -> dict[str, str]:
    flux_rules = load_flux2_prompting().get("wan", {})
    flux_rule_block = _rule_block(
        flux_rules,
        "natural_language_contract",
        "hierarchy",
        "emphasis",
        "suppression",
    )
    schema = {
        "type": "object",
        "properties": {
            "shots": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "shot_id": {"type": "string"},
                        "positive_prompt_text": {"type": "string"},
                    },
                    "required": ["shot_id", "positive_prompt_text"],
                },
            }
        },
        "required": ["shots"],
    }
    prompt = (
        "You are a render verbalizer for a Wan first-last-frame bridge pipeline. "
        "Your job is only to merge already-decided clauses into one natural English positive prompt. "
        "Preserve meaning exactly. Do not add any new person, place, prop, action, relationship, emotion, symbolism, or story information. "
        f"{flux_rule_block} "
        f"{_instruction_block('wan_instruction_lines')} "
        "Return JSON only.\n\n"
        f"Shots={rows}"
    )
    raw = generate_structured(config, prompt, schema, attempts=1)
    out: dict[str, str] = {}
    for row in raw.get("shots", []):
        if not isinstance(row, dict):
            continue
        shot_id = str(row.get("shot_id", "")).strip()
        text = " ".join(str(row.get("positive_prompt_text", "")).strip().split())
        if shot_id and text:
            out[shot_id] = text
    return out


def _join_prompt_parts(*parts: object) -> str:
    return " ".join(sentence for sentence in (_sentence(part) for part in parts) if sentence)


def _sentence(text: object) -> str:
    cleaned = " ".join(str(text).strip().rstrip(". ").split())
    return f"{cleaned}." if cleaned else ""


def _rule_block(rules: dict, *keys: str) -> str:
    return " ".join(
        str(rules.get(key, "")).strip()
        for key in keys
        if str(rules.get(key, "")).strip()
    )


def _instruction_block(name: str) -> str:
    rows = load_render_verbalizer_rules().get(name, [])
    if not isinstance(rows, list):
        return ""
    return " ".join(str(row).strip() for row in rows if str(row).strip())


def _ref_subject(row: dict, brief: dict) -> str:
    subject = str(brief.get("anchor_subject", "")).strip()
    if subject:
        return f"The woman"
    intro = str(row.get("subject_intro", "")).strip()
    if "woman" in intro.lower():
        return "The woman"
    return "The woman"


def _action_clause(row: dict, phase: str) -> str:
    if phase == "start":
        raw = str(row.get("start_state", "")).strip() or str(row.get("dominant_action", "")).strip()
    else:
        raw = str(row.get("dominant_action", "")).strip() or str(row.get("end_state", "")).strip()
    cleaned = _strip_leading_subject(raw)
    lowered = cleaned.lower()
    if lowered.startswith(("walking ", "standing ", "sitting ", "crossing ", "leaning ", "holding ", "playing ", "stepping ", "pausing ")):
        return cleaned
    replacements = {
        "keeps ": "keeping ",
        "lets ": "letting ",
        "moves ": "moving ",
        "enters ": "entering ",
        "carries ": "carrying ",
        "takes ": "taking ",
        "lands ": "landing ",
        "sets ": "setting ",
        "walks ": "walking ",
        "steps ": "stepping ",
        "braces ": "bracing ",
        "holds ": "holding ",
        "leans ": "leaning ",
        "rests ": "resting ",
        "sits ": "sitting ",
        "interacts ": "interacting ",
        "opens ": "opening ",
        "appears ": "appearing ",
        "plays ": "playing ",
        "writes ": "writing ",
        "closes ": "closing ",
        "crosses ": "crossing ",
        "stands ": "standing ",
        "touches ": "touching ",
        "passes ": "passing ",
    }
    for prefix, replacement in replacements.items():
        if lowered.startswith(prefix):
            return replacement + cleaned[len(prefix):]
    if cleaned:
        return cleaned[0].lower() + cleaned[1:] if len(cleaned) > 1 else cleaned.lower()
    return "holding still for a brief cinematic beat"


def _place_clause(row: dict, previous: dict | None) -> str:
    surface = _clean_phrase(row.get("primary_surface", ""))
    location = _clean_phrase(row.get("location", ""))
    previous_surface = _clean_phrase(previous.get("primary_surface", "")) if isinstance(previous, dict) else ""
    continuity_anchor = _clean_phrase(row.get("continuity_anchor", ""))
    if surface and previous_surface and surface == previous_surface:
        return f"The same location stays around her, with {surface} still anchoring the frame."
    if continuity_anchor:
        return _continuity_anchor_sentence(continuity_anchor)
    if surface:
        return f"The scene is grounded by {surface}."
    if location:
        return f"The scene stays grounded {location.lower()}."
    return ""


def _support_parts(row: dict, previous: dict | None, phase: str) -> list[str]:
    trace = _clean_phrase(row.get("literal_image", "")) or _clean_phrase(row.get("support_detail", "")) or _clean_phrase(row.get("content_trace", ""))
    event = _clean_phrase(row.get("story_event", ""))
    continuity = _clean_phrase(row.get("end_state", "")) if phase == "end" else ""
    emotional_turn = _clean_phrase(row.get("emotional_turn", ""))
    previous_event = _clean_phrase(previous.get("story_event", "")) if isinstance(previous, dict) else ""
    pieces: list[str] = []
    if trace:
        pieces.append(trace)
    if emotional_turn and _looks_like_english_clause(emotional_turn) and not _looks_like_meta_event(emotional_turn):
        pieces.append(emotional_turn)
    if event and event != previous_event and not _looks_like_meta_event(event) and not _same_motion_family(event, row.get("dominant_action", "")):
        pieces.append(event)
    if continuity and continuity != _clean_phrase(row.get("dominant_action", "")) and not _looks_like_meta_continuity(continuity):
        pieces.append(continuity)
    return [_capitalize_fragment(piece) for piece in pieces if piece]


def _cinematic_finish(brief: dict, row: dict) -> str:
    genre = str(brief.get("profile_genre", "")).lower()
    section = str(row.get("section_label", "")).lower()
    surface = str(row.get("primary_surface", "")).lower()
    if any(token in surface for token in ("street", "crosswalk", "road", "sidewalk", "curb", "lane")):
        lens = "anamorphic lens"
        lighting = "natural streetlight contrast"
    elif any(token in surface for token in ("window", "diner", "room", "club", "interior", "passage")):
        lens = "35mm photography"
        lighting = "soft practical lighting"
    else:
        lens = "cinematic lensing"
        lighting = "natural cinematic lighting"
    if "rock" in genre:
        texture = "documentary realism"
    elif "synth" in genre or "pop" in genre:
        texture = "subtle film grain"
    else:
        texture = "film grain"
    dof = "shallow depth of field" if "chorus" not in section else "controlled depth of field"
    return f"{_capitalize_fragment(lighting)}, {texture}, {dof}, {lens}."


def _strip_leading_subject(text: str) -> str:
    cleaned = _clean_phrase(text)
    low = cleaned.lower()
    for prefix in ("she ", "the woman ", "the same heroine ", "the same korean female idol "):
        if low.startswith(prefix):
            return cleaned[len(prefix):]
    return cleaned


def _clean_phrase(text: object) -> str:
    return " ".join(str(text).strip().rstrip(". ").split())


def _capitalize_fragment(text: str) -> str:
    cleaned = _clean_phrase(text)
    if not cleaned:
        return ""
    return cleaned[0].upper() + cleaned[1:]


def _looks_like_meta_event(text: str) -> bool:
    lowered = _clean_phrase(text).lower()
    meta_tokens = (
        "the song so far",
        "the scene",
        "the mood",
        "the place",
        "the final image",
    )
    return any(token in lowered for token in meta_tokens)


def _looks_like_meta_continuity(text: str) -> bool:
    lowered = _clean_phrase(text).lower()
    meta_tokens = (
        "place continuity",
        "grounded reality",
        "release without losing",
        "moment forward",
        "next movement already forming",
        "consistent from the previous shot",
        "keep the same",
    )
    return any(token in lowered for token in meta_tokens)


def _looks_like_english_clause(text: str) -> bool:
    lowered = _clean_phrase(text).lower()
    words = [w for w in lowered.split() if w]
    if len(words) < 2:
        return False
    alpha_words = sum(1 for w in words if any("a" <= ch <= "z" for ch in w))
    return alpha_words >= max(2, len(words) // 2)


def _continuity_anchor_sentence(anchor: str) -> str:
    cleaned = _clean_phrase(anchor)
    if not cleaned:
        return ""
    lowered = cleaned.lower()
    if lowered.startswith("the same "):
        subject = cleaned[9:]
        return f"The same {subject} stays with her."
    return f"{_capitalize_fragment(cleaned)} remains visible."


def _same_motion_family(left: object, right: object) -> bool:
    left_low = _clean_phrase(left).lower()
    right_low = _clean_phrase(right).lower()
    verb_families = (
        ("move", "moving", "moves"),
        ("walk", "walking", "walks"),
        ("open", "opening", "opens"),
        ("enter", "entering", "enters"),
        ("interact", "interacting", "interacts"),
        ("hold", "holding", "holds"),
        ("pause", "pausing", "pauses"),
        ("step", "stepping", "steps"),
        ("touch", "touching", "touches"),
        ("pass", "passing", "passes"),
    )
    for family in verb_families:
        if any(token in left_low for token in family) and any(token in right_low for token in family):
            return True
    return False


def _lead_sentence(subject: str, action: str, place: str) -> str:
    action_text = _clean_phrase(action)
    place_text = _clean_phrase(place)
    if not action_text:
        return ""
    if place_text.startswith("The same ") or place_text.startswith("The scene "):
        return _sentence(f"{subject} is {action_text}")
    if place_text:
        if place_text.endswith("."):
            place_text = place_text[:-1]
        if place_text.lower().startswith(("in ", "at ", "by ", "along ")):
            return _sentence(f"{subject} is {action_text}, {place_text.lower()}")
        return _sentence(f"{subject} is {action_text}. {place_text}")
    return _sentence(f"{subject} is {action_text}")
