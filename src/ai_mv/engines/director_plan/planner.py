from __future__ import annotations

from ai_mv.core.contracts.visual_plan_normalize import normalize_direction_plan
from ai_mv.core.director_brief import build_director_brief_intent


def build_direction_plan(config: dict, payload: dict) -> dict:
    brief = build_director_brief_intent(config)
    outline = payload.get("wan_safe_scene_outline", payload["scene_outline"])
    shot_packages: list[dict] = []
    for shot in outline.get("shot_packages", []):
        current = dict(shot)
        place = _resolve_place(brief, current)
        action = _resolve_action(current)
        carry = _resolve_carry(brief, current)
        current.update(
            {
                "shot_function": _shot_function(str(current.get("shot_role", "")).strip(), str(current.get("payoff_role", "")).strip()),
                "place": place,
                "action": action,
                "carry": carry,
                "framing": _resolve_framing(current, place),
            }
        )
        shot_packages.append(current)
    return normalize_direction_plan(
        {
            "brief_name": brief["brief_name"],
            "story_premise": brief["story_premise"],
            "shot_packages": shot_packages,
        }
    )


def build_director_plan(config: dict, payload: dict) -> dict:
    return build_direction_plan(config, payload)


def build_direction_plan_preview_prompt(config: dict, payload: dict) -> str:
    brief = build_director_brief_intent(config)
    return (
        "Resolve each lyric-driven scene beat into only three visual decisions: place, visible action, and carry-over detail. "
        f"Story premise={brief['story_premise']}. "
        "Do not classify style families or write final prompts here."
    )


def build_director_plan_preview_prompt(config: dict, payload: dict) -> str:
    return build_direction_plan_preview_prompt(config, payload)


def _shot_function(shot_role: str, payoff_role: str) -> str:
    mapping = {
        "setup": "setup",
        "carry": "carry",
        "tighten": "tighten",
        "handoff": "handoff",
        "release": "release",
    }
    if payoff_role == "release":
        return "release"
    return mapping.get(shot_role, "carry")


def _resolve_place(brief: dict, shot: dict) -> str:
    literal_image = str(shot.get("literal_image", "")).strip()
    inferred = _literal_place(literal_image)
    if inferred:
        return inferred
    locations = [str(x).strip() for x in brief.get("profile_locations", []) if str(x).strip()]
    section = str(shot.get("section_label", "")).strip().lower()
    story_function = str(shot.get("shot_role", "")).strip().lower()
    if locations:
        if "intro" in section or "verse 1" in section:
            return locations[0]
        if ("bridge" in section or "final chorus" in section or "outro" in section) and len(locations) >= 3:
            return locations[2]
        if ("chorus" in section or story_function == "release") and len(locations) >= 2:
            return locations[1]
        if len(locations) >= 2:
            return locations[1]
        return locations[0]
    return "a grounded real-world location"


def _resolve_action(shot: dict) -> str:
    visible_action = _clean(str(shot.get("visible_action", "")).strip())
    if visible_action:
        return _to_ing(_strip_subject(visible_action))
    story_function = str(shot.get("shot_role", "")).strip()
    fallback = {
        "setup": "moving into the frame naturally",
        "carry": "continuing forward through the same place",
        "tighten": "holding a tighter, shorter pause",
        "handoff": "landing in the next readable state",
        "release": "opening into the clearest release",
    }
    return fallback.get(story_function, "continuing through the same place")


def _resolve_carry(brief: dict, shot: dict) -> str:
    continuity_anchor = _clean(str(shot.get("continuity_anchor", "")).strip())
    if continuity_anchor:
        return continuity_anchor
    props = [str(x).strip() for x in brief.get("profile_props", []) if str(x).strip()]
    if props:
        return ", ".join(props[:2])
    literal_image = _clean(str(shot.get("literal_image", "")).strip())
    return literal_image


def _resolve_framing(shot: dict, place: str) -> str:
    shot_function = str(shot.get("shot_function", "") or shot.get("shot_role", "")).strip().lower()
    low_place = place.lower()
    if shot_function == "tighten":
        return "medium close framing"
    if shot_function == "release":
        return "medium-wide full-body framing"
    if any(token in low_place for token in ("street", "crosswalk", "intersection", "road", "sidewalk", "rooftop")):
        return "medium-wide full-body framing"
    return "three-quarter medium framing"


def _strip_subject(text: str) -> str:
    low = text.lower()
    for prefix in ("she is ", "she ", "he is ", "he ", "they are ", "they ", "the woman is ", "the woman ", "the man is ", "the man ", "the performer is ", "the performer "):
        if low.startswith(prefix):
            return text[len(prefix):].strip()
    return text


def _clean(text: str) -> str:
    return " ".join(text.strip().rstrip(". ").split())


def _literal_place(text: str) -> str:
    low = text.lower()
    if any(token in low for token in ("diner", "cafe", "booth", "mug", "window")):
        return "dim late-night diner"
    if any(token in low for token in ("crosswalk", "asphalt", "headlight", "sidewalk", "street", "intersection")):
        return "wet city street at night"
    if any(token in low for token in ("club", "synthesizer", "cables", "stage")):
        return "cramped rehearsal room"
    if any(token in low for token in ("rooftop", "skyline", "dawn", "fog")):
        return "concrete rooftop at dawn"
    return ""


def _to_ing(text: str) -> str:
    cleaned = _clean(text)
    low = cleaned.lower()
    direct = (
        "walking ",
        "standing ",
        "sitting ",
        "crossing ",
        "leaning ",
        "holding ",
        "playing ",
        "stepping ",
        "pausing ",
        "writing ",
        "looking ",
        "turning ",
        "moving ",
    )
    if low.startswith(direct):
        return cleaned
    replacements = {
        "walks ": "walking ",
        "stands ": "standing ",
        "sits ": "sitting ",
        "crosses ": "crossing ",
        "leans ": "leaning ",
        "holds ": "holding ",
        "plays ": "playing ",
        "steps ": "stepping ",
        "pauses ": "pausing ",
        "writes ": "writing ",
        "looks ": "looking ",
        "turns ": "turning ",
        "moves ": "moving ",
    }
    for prefix, replacement in replacements.items():
        if low.startswith(prefix):
            cleaned = replacement + cleaned[len(prefix):]
            break
    cleaned = cleaned.replace(" and looks ", " and looking ")
    cleaned = cleaned.replace(" and turns ", " and turning ")
    cleaned = cleaned.replace(" and holds ", " and holding ")
    cleaned = cleaned.replace(" and steps ", " and stepping ")
    cleaned = cleaned.replace(" and crosses ", " and crossing ")
    return cleaned
