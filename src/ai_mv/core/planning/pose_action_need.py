from __future__ import annotations

import re
from typing import Any

from ai_mv.core.planning.pose_anchor_selection import build_pose_anchor_selection


_DEFAULT_QA_REQUIREMENTS = [
    "same_identity",
    "same_wardrobe",
    "single_protagonist",
    "source_bound_world",
]


def build_pose_action_need(shot: dict[str, Any], concept_text: str = "") -> dict[str, Any]:
    """Build structured, source-bound pose/action need metadata for a shot.

    This is a deterministic planning layer: it summarizes what the shot needs
    before prompts are assembled. It must not turn negative-only concept terms
    into positive pose/world sources.
    """

    positive_concept = _positive_source_text(concept_text)
    text = _shot_text(shot, positive_concept)
    selection = build_pose_anchor_selection({**shot, "concept_text": concept_text})
    anchor_id = str(selection.get("selected_pose_anchor_id", "")).strip()
    pose_family = str(selection.get("required_pose_family", "")).strip()
    world_interaction, source_terms = _world_interaction(text, positive_concept)
    if world_interaction == "standing in source-bound lighthouse cliff wind":
        pose_family = "full_body"
    risk_tier = _risk_tier(anchor_id, pose_family, world_interaction)
    camera_angle = str(selection.get("required_camera_angle", "")).strip() or "front_three_quarter"
    framing = str(selection.get("required_framing", "")).strip() or "medium"
    motion_direction = str(selection.get("required_motion_direction", "")).strip() or _motion_direction(pose_family)
    body_action = str(selection.get("required_body_action", "")).strip() or _body_action(pose_family, world_interaction)

    return {
        "schema_version": "pose_action_need_v1",
        "selected_pose_anchor_id": anchor_id,
        "pose_family": pose_family,
        "framing": framing,
        "camera_angle": camera_angle,
        "subject_position": str(selection.get("required_subject_position", "")).strip() or "center",
        "body_action": body_action,
        "motion_direction": motion_direction,
        "face_readability": _face_readability(anchor_id, camera_angle, framing),
        "wardrobe_readability": _wardrobe_readability(anchor_id, framing),
        "allowed_props": _allowed_props(text),
        "world_interaction": world_interaction,
        "source_bound_terms": source_terms,
        "risk_tier": risk_tier,
        "qa_requirements": list(_DEFAULT_QA_REQUIREMENTS),
    }


def _shot_text(shot: dict[str, Any], positive_concept: str) -> str:
    pieces: list[str] = [positive_concept]
    for key in ("shot_id", "section_type", "shot_role", "visual_mode", "story_function"):
        pieces.append(str(shot.get(key, "")))
    story = shot.get("story_contract", {})
    if isinstance(story, dict):
        for key in ("why_this_shot", "protagonist_action", "world_action", "emotional_state"):
            pieces.append(str(story.get(key, "")))
    return _normalize(" ".join(pieces))


def _positive_source_text(text: object) -> str:
    pieces: list[str] = []
    for raw_part in str(text or "").lower().replace(";", ",").split(","):
        part = raw_part.strip()
        if not part:
            continue
        if part.startswith(("no ", "without ", "avoid ", "never ")):
            continue
        pieces.append(part)
    return _normalize(" ".join(pieces).replace("_", " "))


def _world_interaction(text: str, positive_concept: str) -> tuple[str, list[str]]:
    positive = f"{positive_concept} {text}"
    if _has_any(positive, ("greenhouse", "glasshouse", "seedling", "seedlings", "plant", "plants")):
        terms = []
        if _has_any(positive, ("greenhouse", "glasshouse")):
            terms.append("greenhouse")
        if _has_any(positive, ("seedling", "seedlings")):
            terms.append("seedlings")
            terms.append("plants")
        if _has_any(positive, ("plant", "plants")):
            terms.append("plants")
        return "tending source-bound seedlings or plants", _dedupe(terms)
    if _has_any(positive, ("lighthouse", "cliff", "cliffs", "ocean", "wind", "windbreaker")):
        terms = []
        if "lighthouse" in positive:
            terms.append("lighthouse")
        if _has_any(positive, ("cliff", "cliffs")):
            terms.append("cliff")
        if _has_any(positive, ("ocean", "wind", "windbreaker")):
            terms.append("wind")
        return "standing in source-bound lighthouse cliff wind", _dedupe(terms)
    if _has_any(positive, ("arctic", "ice", "snow", "aurora")):
        terms = []
        for term in ("arctic", "ice", "snow", "aurora"):
            if term in positive:
                terms.append(term)
        return "moving through source-bound arctic ice field", _dedupe(terms)
    return "source-bound movement through established world", []


def _risk_tier(anchor_id: str, pose_family: str, world_interaction: str) -> str:
    if anchor_id in {
        "ANCHOR_POSE_HERO_CLOSEUP",
        "ANCHOR_POSE_THREE_QUARTER_MEDIUM",
        "ANCHOR_POSE_FULL_BODY_STANDING",
        "ANCHOR_POSE_FINAL_PAYOFF_FRONT",
    }:
        return "low"
    if anchor_id == "ANCHOR_POSE_MICROPHONE_PERFORMANCE":
        return "high"
    if "tending" in world_interaction:
        return "medium"
    if pose_family in {"walking", "walking_toward", "seated_waiting", "expressive_hand_gesture", "profile"}:
        return "medium"
    return "medium"


def _face_readability(anchor_id: str, camera_angle: str, framing: str) -> str:
    if anchor_id in {"ANCHOR_POSE_FINAL_PAYOFF_FRONT", "ANCHOR_POSE_HERO_CLOSEUP"}:
        return "high"
    if camera_angle == "front" and framing in {"medium", "close", "medium_close"}:
        return "high"
    if "profile" in camera_angle:
        return "medium"
    return "medium"


def _wardrobe_readability(anchor_id: str, framing: str) -> str:
    if anchor_id in {"ANCHOR_POSE_FINAL_PAYOFF_FRONT", "ANCHOR_POSE_HERO_CLOSEUP"}:
        return "upper_body_required"
    if framing in {"full", "medium"}:
        return "full_body_required"
    return "upper_body_required"


def _motion_direction(pose_family: str) -> str:
    if pose_family == "walking":
        return "sideways"
    if pose_family == "walking_toward":
        return "toward_camera"
    return "static"


def _body_action(pose_family: str, world_interaction: str) -> str:
    if "tending" in world_interaction:
        return "careful source-bound tending gesture"
    if pose_family:
        return pose_family
    return "static readable pose"


def _allowed_props(text: str) -> list[str]:
    # Keep prop allowance deliberately narrow. Object-specific props are added
    # only from explicit positive action sources and should not include negative
    # copy such as "no microphone".
    if "microphone" in text and "no microphone" not in text and "without microphone" not in text:
        return ["microphone"]
    return []


def _has_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(re.search(rf"(?<![a-z]){re.escape(marker)}(?![a-z])", text) for marker in markers)


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").lower()).strip()


def _dedupe(values: list[str]) -> list[str]:
    out: list[str] = []
    for value in values:
        if value and value not in out:
            out.append(value)
    return out
