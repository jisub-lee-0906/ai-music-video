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
        "required_body_action": "walking_side",
        "required_motion_direction": "sideways",
        "required_prop": "none",
        "reason": "movement/search/release shots need a side walking pose instead of static portrait collapse",
    },
    "ANCHOR_POSE_WALKING_TOWARD": {
        "pose_family": "walking_toward",
        "required_framing": "full",
        "required_camera_angle": "front",
        "required_subject_position": "center",
        "required_body_action": "walking_toward",
        "required_motion_direction": "toward_camera",
        "required_prop": "none",
        "reason": "forward-motion shots need a toward-camera walking anchor instead of side walking re-instantiation",
    },
    "ANCHOR_POSE_SEATED_WAITING": {
        "pose_family": "seated_waiting",
        "required_framing": "medium",
        "required_camera_angle": "front_three_quarter",
        "required_subject_position": "center",
        "required_body_action": "seated_waiting",
        "required_motion_direction": "static",
        "required_prop": "none",
        "reason": "waiting or window/bench shots need a seated pose card instead of forcing standing anatomy",
    },
    "ANCHOR_POSE_EXPRESSIVE_HAND_GESTURE": {
        "pose_family": "expressive_hand_gesture",
        "required_framing": "medium",
        "required_camera_angle": "front_three_quarter",
        "required_subject_position": "center",
        "required_body_action": "expressive_hand_gesture",
        "required_motion_direction": "static",
        "required_prop": "none",
        "reason": "objectless chorus/emotional shots need a hand gesture anchor without defaulting to microphone grammar",
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
    if _has_toward_camera_action(text):
        return _selection("ANCHOR_POSE_WALKING_TOWARD")
    if _has_seated_waiting_action(text):
        return _selection("ANCHOR_POSE_SEATED_WAITING")
    if _has_expressive_hand_action(text):
        return _selection("ANCHOR_POSE_EXPRESSIVE_HAND_GESTURE")
    if _has_final_payoff_intent(shot, text, story_function):
        return _selection("ANCHOR_POSE_FINAL_PAYOFF_FRONT", decision=_final_payoff_decision())
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


def _selection(anchor_id: str, decision: dict | None = None) -> dict:
    spec = POSE_ANCHOR_CATALOG[anchor_id]
    selection = {
        "selected_pose_anchor_id": anchor_id,
        "required_pose_family": spec["pose_family"],
        "required_framing": spec["required_framing"],
        "required_camera_angle": spec["required_camera_angle"],
        "required_subject_position": spec["required_subject_position"],
        "anchor_selection_reason": spec["reason"],
        "fallback_anchor_ids": ["ANCHOR_CHARACTER_UPPER_BODY", "ANCHOR_CHARACTER_FULL_BODY"],
    }
    if decision:
        selection.update(decision)
    for key in ("required_body_action", "required_motion_direction", "required_prop"):
        if key in spec:
            selection[key] = spec[key]
    return selection


def _has_any_word(text: str, words: tuple[str, ...]) -> bool:
    return any(re.search(rf"(?<![a-z]){re.escape(word)}(?![a-z])", text) for word in words)


def _has_microphone_action(text: str) -> bool:
    positive_markers = ("microphone", "mic stand", "handheld mic", "singing into a mic")
    return any(marker in text and not _is_negated_action(text, marker) for marker in positive_markers)


def _has_toward_camera_action(text: str) -> bool:
    markers = (
        "walks toward camera",
        "walking toward camera",
        "walk toward camera",
        "toward camera",
        "towards camera",
        "approaches camera",
        "approach camera",
        "forward motion",
    )
    return any(marker in text for marker in markers)


def _has_seated_waiting_action(text: str) -> bool:
    seated = any(marker in text for marker in ("seated", "sits ", "sit ", "sitting"))
    waiting_context = any(marker in text for marker in ("waiting", "waits", "window", "bench", "chair", "stairs", "step"))
    return seated and waiting_context


def _has_expressive_hand_action(text: str) -> bool:
    if _has_microphone_action(text):
        return False
    hand_markers = ("open hand", "hand near chest", "hand gesture", "raises one hand", "reaches out", "reaching hand")
    objectless_markers = ("empty hands", "without props", "no prop", "no microphone", "without microphone")
    return any(marker in text for marker in hand_markers) and any(marker in text for marker in objectless_markers)


def _has_final_payoff_intent(shot: dict, text: str, story_function: str) -> bool:
    if _has_unresolved_or_pre_final_context(text):
        return False
    section_type = str(shot.get("section_type", "")).strip().lower().replace("_", " ")
    visual_mode = str(shot.get("visual_mode", "")).strip().lower().replace("_", " ")
    if story_function in {"payoff", "final_payoff", "resolution"}:
        return True
    if section_type in {"outro", "finale", "ending"} and _has_resolution_language(text):
        return True
    if "final payoff" in text or "final visual payoff" in text or "resolved payoff" in text:
        return True
    return "final payoff" in visual_mode or "payoff front" in visual_mode


def _has_resolution_language(text: str) -> bool:
    return _has_any_word(text, ("payoff", "resolve", "resolved", "resolution", "ending"))


def _has_unresolved_or_pre_final_context(text: str) -> bool:
    blocked_phrases = (
        "unresolved",
        "not yet resolved",
        "not resolved",
        "not reached the final payoff",
        "before the final",
        "pre final",
        "pre-final",
        "still searching",
        "searching before",
    )
    return any(phrase in text for phrase in blocked_phrases)


def _final_payoff_decision() -> dict:
    return {
        "decision_method": "structured_shot_semantics",
        "reason_codes": ["final_payoff_positive_resolution", "front_medium_resolved_identity_readability"],
        "shot_semantics": {
            "final_payoff": True,
            "resolution_state": "resolved",
            "body_action": "front_facing_resolved_pose",
            "framing": "medium",
            "camera_angle": "front",
            "prop": "none",
        },
        "rejected_anchor_ids": {
            "ANCHOR_POSE_HERO_CLOSEUP": "final payoff needs resolved medium front hero framing, not generic closeup",
            "ANCHOR_POSE_THREE_QUARTER_MEDIUM": "final payoff should face the viewer instead of bridge three-quarter staging",
            "ANCHOR_POSE_WALKING_SIDE": "final payoff is a resolved hold, not a movement/search shot",
        },
    }


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
