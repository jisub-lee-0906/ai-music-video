from __future__ import annotations

import re


POSE_ANCHOR_CATALOG: dict[str, dict] = {
    "ANCHOR_POSE_HERO_CLOSEUP": {
        "pose_family": "hero_closeup",
        "required_framing": "close",
        "required_camera_angle": "front",
        "required_subject_position": "center",
        "reason": "hero or threshold shots need a readable face-forward emotional identity anchor",
    },
    "ANCHOR_POSE_THREE_QUARTER_MEDIUM": {
        "pose_family": "three_quarter",
        "required_framing": "medium",
        "required_camera_angle": "three_quarter",
        "required_subject_position": "left_third",
        "reason": "search or bridge shots need non-front torso angle while preserving face readability",
    },
    "ANCHOR_POSE_FULL_BODY_STANDING": {
        "pose_family": "full_body",
        "required_framing": "full",
        "required_camera_angle": "front",
        "required_subject_position": "center",
        "reason": "establishing and world-bridge shots need full silhouette continuity",
    },
    "ANCHOR_POSE_WALKING_SIDE": {
        "pose_family": "walking",
        "required_framing": "full",
        "required_camera_angle": "side",
        "required_subject_position": "right_third",
        "reason": "movement/search/release shots need a side walking pose instead of static portrait collapse",
    },
    "ANCHOR_POSE_PROFILE_EMOTIONAL": {
        "pose_family": "profile",
        "required_framing": "medium_close",
        "required_camera_angle": "profile",
        "required_subject_position": "left_third",
        "reason": "emotional turn shots need profile variation while keeping hair and face outline readable",
    },
    "ANCHOR_POSE_FINAL_PAYOFF_FRONT": {
        "pose_family": "final_payoff_front",
        "required_framing": "medium",
        "required_camera_angle": "front",
        "required_subject_position": "center",
        "reason": "payoff shots need a resolved front-facing hero anchor distinct from generic close-up",
    },
    "ANCHOR_POSE_MICROPHONE_PERFORMANCE": {
        "pose_family": "microphone_performance",
        "required_framing": "medium",
        "required_camera_angle": "front_three_quarter",
        "required_subject_position": "center",
        "reason": "microphone performance shots need a prop/action-matched pose card before IA2V",
    },
}


def build_pose_anchor_selection(shot: dict) -> dict:
    text = _shot_text(shot)
    story_function = str(shot.get("story_function", "")).strip().lower()
    if _has_microphone_action(text):
        return _selection("ANCHOR_POSE_MICROPHONE_PERFORMANCE")
    if story_function == "payoff" or _has_any_word(text, ("payoff", "final", "resolve", "resolved")):
        return _selection("ANCHOR_POSE_FINAL_PAYOFF_FRONT")
    if _has_any_word(text, ("walk", "walking", "side", "movement")) or "forward motion" in text or story_function in {"search", "release"} and "close" not in text:
        return _selection("ANCHOR_POSE_WALKING_SIDE")
    if any(token in text for token in ("profile", "looking down", "over shoulder", "over-shoulder")):
        return _selection("ANCHOR_POSE_PROFILE_EMOTIONAL")
    if any(token in text for token in ("full body", "full-body", "wide", "world", "establish")):
        return _selection("ANCHOR_POSE_FULL_BODY_STANDING")
    if any(token in text for token in ("hero", "close", "closeup", "close-up", "threshold")) or story_function == "threshold":
        return _selection("ANCHOR_POSE_HERO_CLOSEUP")
    if any(token in text for token in ("three quarter", "three-quarter", "bridge")):
        return _selection("ANCHOR_POSE_THREE_QUARTER_MEDIUM")
    if "emotional" in text:
        return _selection("ANCHOR_POSE_HERO_CLOSEUP")
    return _selection("ANCHOR_POSE_THREE_QUARTER_MEDIUM")


def _selection(anchor_id: str) -> dict:
    spec = POSE_ANCHOR_CATALOG[anchor_id]
    return {
        "selected_pose_anchor_id": anchor_id,
        "required_pose_family": spec["pose_family"],
        "required_framing": spec["required_framing"],
        "required_camera_angle": spec["required_camera_angle"],
        "required_subject_position": spec["required_subject_position"],
        "anchor_selection_reason": spec["reason"],
        "fallback_anchor_ids": ["ANCHOR_CHARACTER_UPPER_BODY", "ANCHOR_CHARACTER_FULL_BODY"],
    }


def _has_any_word(text: str, words: tuple[str, ...]) -> bool:
    return any(re.search(rf"(?<![a-z]){re.escape(word)}(?![a-z])", text) for word in words)


def _has_microphone_action(text: str) -> bool:
    positive_markers = ("microphone", "mic stand", "handheld mic", "singing into a mic")
    return any(marker in text and not _is_negated_action(text, marker) for marker in positive_markers)


def _is_negated_action(text: str, marker: str) -> bool:
    normalized_marker = marker.replace("_", " ")
    negated_forms = (
        f"no {normalized_marker}",
        f"without {normalized_marker}",
        f"avoid {normalized_marker}",
        f"not {normalized_marker}",
        f"never {normalized_marker}",
    )
    if any(form in text for form in negated_forms):
        return True
    if marker == "microphone" and ("no microphone" in text or "without microphone" in text):
        return True
    return False


def _shot_text(shot: dict) -> str:
    parts = []
    for key in ("shot_id", "shot_role", "visual_mode", "story_function", "visual_event", "emotional_state", "section_type"):
        parts.append(str(shot.get(key, "")))
    story_contract = shot.get("story_contract") if isinstance(shot.get("story_contract"), dict) else {}
    for key in ("why_this_shot", "protagonist_action"):
        parts.append(str(story_contract.get(key, "")))
    return " ".join(parts).replace("_", " ").lower()
