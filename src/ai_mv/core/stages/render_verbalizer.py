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
    support = _support_clause(row, previous, phase)
    finish = _cinematic_finish(brief, row)
    parts = [
        _sentence(f"{subject} is {action}"),
        _sentence(place),
        support,
        finish,
        "Keep the face.",
    ]
    return " ".join(part for part in parts if part).strip()


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
    if surface and previous_surface and surface == previous_surface:
        return f"The same place continues around her with {surface} still anchoring the frame."
    if surface:
        return f"The scene is grounded by {surface}."
    if location:
        return f"The scene stays grounded {location.lower()}."
    return ""


def _support_clause(row: dict, previous: dict | None, phase: str) -> str:
    trace = _clean_phrase(row.get("support_detail", "")) or _clean_phrase(row.get("content_trace", ""))
    event = _clean_phrase(row.get("story_event", ""))
    continuity = _clean_phrase(row.get("end_state", "")) if phase == "end" else ""
    previous_event = _clean_phrase(previous.get("story_event", "")) if isinstance(previous, dict) else ""
    pieces: list[str] = []
    if trace:
        pieces.append(trace)
    if event and event != previous_event:
        pieces.append(event)
    if continuity and continuity != _clean_phrase(row.get("dominant_action", "")):
        pieces.append(continuity)
    if not pieces:
        return ""
    sentence = ". ".join(_capitalize_fragment(piece) for piece in pieces if piece)
    return _sentence(sentence)


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
