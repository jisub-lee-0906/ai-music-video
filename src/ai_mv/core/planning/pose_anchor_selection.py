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
    "ANCHOR_POSE_GREENHOUSE_TENDING": {
        "pose_family": "greenhouse_tending",
        "required_framing": "medium",
        "required_camera_angle": "front_three_quarter",
        "required_subject_position": "center",
        "required_body_action": "source_bound_seedling_tending",
        "required_motion_direction": "static",
        "required_prop": "none",
        "reason": "source-bound greenhouse/seedling shots need a tending gesture pose instead of generic walking grammar",
    },
    "ANCHOR_POSE_LIGHTHOUSE_CLIFF_STANCE": {
        "pose_family": "lighthouse_cliff_stance",
        "required_framing": "full",
        "required_camera_angle": "front_three_quarter",
        "required_subject_position": "center",
        "required_body_action": "source_bound_cliff_wind_stance",
        "required_motion_direction": "static",
        "required_prop": "none",
        "reason": "source-bound lighthouse/cliff/wind search shots need a stable cliff stance instead of generic walking",
    },
    "ANCHOR_POSE_LIGHTHOUSE_LOOKOUT_STANCE": {
        "pose_family": "lighthouse_lookout_stance",
        "required_framing": "full",
        "required_camera_angle": "front_three_quarter",
        "required_subject_position": "left_third",
        "required_body_action": "source_bound_lighthouse_lookout_pause",
        "required_motion_direction": "static",
        "required_prop": "none",
        "reason": "source-bound lighthouse wound/setup shots need a lookout pause distinct from search walking grammar",
    },
    "ANCHOR_POSE_LIGHTHOUSE_WIND_FACE": {
        "pose_family": "lighthouse_wind_face",
        "required_framing": "medium",
        "required_camera_angle": "front_three_quarter",
        "required_subject_position": "center",
        "required_body_action": "source_bound_wind_facing_release",
        "required_motion_direction": "static",
        "required_prop": "none",
        "reason": "source-bound lighthouse release shots need a wind-facing resolved stance distinct from search/cliff setup",
    },
    "ANCHOR_POSE_ARCTIC_ICE_CROSSING": {
        "pose_family": "arctic_ice_crossing",
        "required_framing": "full",
        "required_camera_angle": "front_three_quarter",
        "required_subject_position": "center",
        "required_body_action": "source_bound_ice_field_crossing",
        "required_motion_direction": "diagonal_forward",
        "required_prop": "none",
        "reason": "source-bound arctic/ice search shots need crossing movement through the established world",
    },
    "ANCHOR_POSE_ARCTIC_AURORA_LOOKUP": {
        "pose_family": "arctic_aurora_lookup",
        "required_framing": "medium",
        "required_camera_angle": "front_three_quarter",
        "required_subject_position": "center",
        "required_body_action": "source_bound_aurora_lookup_pause",
        "required_motion_direction": "static",
        "required_prop": "none",
        "reason": "source-bound arctic wound/setup shots need an aurora lookup pause distinct from ice crossing",
    },
    "ANCHOR_POSE_ARCTIC_COLD_FIELD_PAUSE": {
        "pose_family": "arctic_cold_field_pause",
        "required_framing": "medium",
        "required_camera_angle": "front_three_quarter",
        "required_subject_position": "center",
        "required_body_action": "source_bound_cold_field_release_pause",
        "required_motion_direction": "static",
        "required_prop": "none",
        "reason": "source-bound arctic release shots need a cold-field pause distinct from search crossing",
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
    if _has_departure_payoff_intent(f"{text} {_positive_source_text(shot.get('concept_text', ''))}", story_function):
        return _selection("ANCHOR_POSE_WALKING_SIDE", decision=_departure_payoff_decision())
    if _has_final_payoff_intent(shot, text, story_function):
        return _selection("ANCHOR_POSE_FINAL_PAYOFF_FRONT", decision=_final_payoff_decision())
    source_bound_selection = _source_bound_world_selection(shot, text, story_function)
    if source_bound_selection:
        return source_bound_selection
    if _has_face_critical_identity_intent(text, story_function):
        return _selection("ANCHOR_POSE_HERO_CLOSEUP")
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


def _source_bound_world_selection(shot: dict, text: str, story_function: str) -> dict | None:
    positive_source = _positive_source_text(shot.get("concept_text", ""))
    if not positive_source:
        return None
    if _has_any_word(positive_source, ("greenhouse", "glasshouse", "seedling", "seedlings", "plant", "plants")) and _has_any_word(
        text, ("tend", "tends", "tending", "seedling", "seedlings", "plant", "plants")
    ):
        return _selection(
            "ANCHOR_POSE_GREENHOUSE_TENDING",
            decision=_source_bound_world_decision("greenhouse_seedling_tending", _greenhouse_source_terms(positive_source)),
        )
    if _has_any_word(positive_source, ("lighthouse", "cliff", "cliffs", "ocean")) and _has_any_word(
        text, ("stand", "stands", "standing", "cliff", "cliffs", "lighthouse", "ocean", "wind", "beacon", "lookout", "threshold", "pause", "pauses")
    ):
        if _story_function_is_setup(story_function) or _has_any_word(text, ("entry", "threshold", "lookout", "pause", "pauses")):
            return _selection(
                "ANCHOR_POSE_LIGHTHOUSE_LOOKOUT_STANCE",
                decision=_source_bound_world_decision("lighthouse_lookout_setup", _lighthouse_source_terms(positive_source)),
            )
        if story_function == "release" and _has_any_word(text, ("chorus", "charge", "wind", "beacon")):
            return _selection(
                "ANCHOR_POSE_LIGHTHOUSE_WIND_FACE",
                decision=_source_bound_world_decision("lighthouse_wind_facing_release", _lighthouse_source_terms(positive_source)),
            )
        return _selection(
            "ANCHOR_POSE_LIGHTHOUSE_CLIFF_STANCE",
            decision=_source_bound_world_decision("lighthouse_cliff_wind_stance", _lighthouse_source_terms(positive_source)),
        )
    if _has_any_word(positive_source, ("arctic", "ice", "snow", "aurora")) and _has_any_word(
        text, ("cross", "crosses", "crossing", "move", "moves", "moving", "walk", "walking", "ice", "snow", "aurora", "look", "looks", "pause", "holds")
    ):
        if story_function == "release" or _has_any_word(text, ("hold", "holds", "still", "pause", "grid", "surge")):
            return _selection(
                "ANCHOR_POSE_ARCTIC_COLD_FIELD_PAUSE",
                decision=_source_bound_world_decision("arctic_cold_field_release_pause", _arctic_source_terms(positive_source)),
            )
        if _story_function_is_setup(story_function) or (
            _has_any_word(text, ("look", "looks", "horizon")) and not _has_any_word(text, ("cross", "crosses", "crossing"))
        ):
            return _selection(
                "ANCHOR_POSE_ARCTIC_AURORA_LOOKUP",
                decision=_source_bound_world_decision("arctic_aurora_lookup_setup", _arctic_source_terms(positive_source)),
            )
        return _selection(
            "ANCHOR_POSE_ARCTIC_ICE_CROSSING",
            decision=_source_bound_world_decision("arctic_ice_field_crossing", _arctic_source_terms(positive_source)),
        )
    return None


def _story_function_is_setup(story_function: str) -> bool:
    return story_function in {"wound_setup", "setup", "opening", "intro", "threshold"}


def _source_bound_world_decision(reason_code: str, source_bound_terms: list[str]) -> dict:
    return {
        "decision_method": "source_bound_pose_action_need",
        "reason_codes": [reason_code, "positive_concept_source_terms_only"],
        "source_bound_terms": source_bound_terms,
    }


def _greenhouse_source_terms(positive_source: str) -> list[str]:
    terms = []
    if _has_any_word(positive_source, ("greenhouse", "glasshouse")):
        terms.append("greenhouse")
    if _has_any_word(positive_source, ("seedling", "seedlings")):
        terms.extend(["seedlings", "plants"])
    elif _has_any_word(positive_source, ("plant", "plants")):
        terms.append("plants")
    return _dedupe(terms)


def _lighthouse_source_terms(positive_source: str) -> list[str]:
    terms = []
    if _has_any_word(positive_source, ("lighthouse",)):
        terms.append("lighthouse")
    if _has_any_word(positive_source, ("cliff", "cliffs")):
        terms.append("cliff")
    if _has_any_word(positive_source, ("ocean", "wind", "windbreaker")):
        terms.append("wind")
    return _dedupe(terms)


def _arctic_source_terms(positive_source: str) -> list[str]:
    return [term for term in ("arctic", "ice", "snow", "aurora") if _has_any_word(positive_source, (term,))]


def _dedupe(values: list[str]) -> list[str]:
    out: list[str] = []
    for value in values:
        if value and value not in out:
            out.append(value)
    return out


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


def _has_departure_payoff_intent(text: str, story_function: str) -> bool:
    if story_function not in {"payoff", "final_payoff", "resolution"} and "payoff" not in text:
        return False
    departure_markers = (
        "walking away into fog",
        "walks away into fog",
        "walk away into fog",
        "turns away into fog",
        "turn away into fog",
        "back view",
        "back-facing",
        "into fog",
        "into the fog",
        "departure",
        "leaves the frame",
        "exit the frame",
        "exits the frame",
    )
    return any(marker in text for marker in departure_markers)


def _positive_source_text(text: object) -> str:
    pieces: list[str] = []
    for raw_part in str(text or "").lower().split(","):
        part = raw_part.strip()
        if not part:
            continue
        if part.startswith(("no ", "without ", "avoid ", "never ")):
            continue
        pieces.append(part)
    return " ".join(pieces).replace("_", " ")


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



def _has_face_critical_identity_intent(text: str, story_function: str) -> bool:
    if story_function == "threshold":
        return True
    return any(token in text for token in ("hero", "close", "closeup", "close-up", "front", "performance"))



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


def _departure_payoff_decision() -> dict:
    return {
        "decision_method": "structured_shot_semantics",
        "reason_codes": ["departure_payoff_motion", "preserve_user_departure_intent"],
        "shot_semantics": {
            "final_payoff": True,
            "resolution_state": "resolved_departure",
            "body_action": "walking_or_turning_away",
            "framing": "full",
            "camera_angle": "side",
            "prop": "none",
        },
        "rejected_anchor_ids": {
            "ANCHOR_POSE_FINAL_PAYOFF_FRONT": "departure payoff should preserve walking-away or turn-away intent instead of forcing front-facing hero hold",
            "ANCHOR_POSE_HERO_CLOSEUP": "departure payoff needs body direction and exit motion, not a static close-up",
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
    for key in ("why_this_shot", "protagonist_action", "visual_event"):
        parts.append(str(story_contract.get(key, "")))
    return " ".join(parts).replace("_", " ").lower()
