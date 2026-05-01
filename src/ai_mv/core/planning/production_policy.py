from __future__ import annotations


_GREEN = "green"
_YELLOW = "yellow"
_RED = "red"


_GENRE_PROFILES = {
    "ACOUSTIC_BALLAD": {
        "prefer": ["close_performance", "bedroom_or_bus_stop", "symbolic_insert", "mic_no_hands"],
        "avoid": ["group_choreography", "dense_crowd", "complex_hand_props"],
    },
    "HIPHOP_STREET": {
        "prefer": ["underpass_solo_performance", "gesture_medium", "street_insert"],
        "avoid": ["dense_crowd", "complex_hand_props", "long_group_blocking"],
    },
    "KPOP_STAGE": {
        "prefer": ["solo_hero_performance", "silhouette_backup", "confetti_stage_payoff"],
        "avoid": ["full_group_choreography_long_take", "dense_crowd_detail", "duplicate_lead_performer"],
    },
    "ROCK_BAND_ROOM": {
        "prefer": ["vocalist", "drummer_silhouette", "band_blur", "mic_no_hands"],
        "avoid": ["precise_guitar_fingering", "long_visible_instrument_hands"],
    },
    "EDM_CLUB_ABSTRACT": {
        "prefer": ["abstract_stage", "light_fog_silhouette", "visualizer_chorus"],
        "avoid": ["identity_heavy_close_narrative", "precise_dialogue_scene"],
    },
    "INDIE_BEDROOM": {
        "prefer": ["intimate_close_performance", "room_practicals", "quiet_insert"],
        "avoid": ["large_crowd", "complex_choreography"],
    },
    "CITYPOP_DRIVE": {
        "prefer": ["car_world_bridge", "hero_performance", "neon_reflection_insert"],
        "avoid": ["long_vehicle_action", "precise_driving_hands"],
    },
    "SURREAL_DREAMPOP": {
        "prefer": ["symbolic_world", "moon_glow_water", "soft_motion"],
        "avoid": ["physical_interaction_realism", "literal_dialogue_scene"],
    },
}


def build_production_policy(shot: dict, *, style_name: str = "") -> dict:
    """Return deterministic production routing/risk policy for an MV shot.

    The policy is intentionally empirical and conservative: it encodes observed
    ComfyUI/IA2V findings as routing metadata rather than pretending every genre
    and material class is equally safe.
    """

    shot = shot if isinstance(shot, dict) else {}
    genre_lane = _genre_lane(shot, style_name)
    candidate_role = _candidate_role(shot)
    anchor_arm = _anchor_arm(candidate_role)
    risk = _risk_class(candidate_role, shot)
    duration = _recommended_duration(candidate_role, risk)
    safety_rules = _safety_rules(candidate_role, risk)
    review_focus = _review_focus(candidate_role, risk)
    genre_profile = _genre_profile(genre_lane)
    if _genre_adds_choreo_or_instrument_risk(shot, genre_profile):
        risk = _max_risk(risk, _YELLOW)
    if candidate_role in {"group_choreography", "instrument_visible_hands"}:
        risk = _max_risk(risk, _YELLOW)

    return {
        "candidate_role": candidate_role,
        "ia2v_risk_class": risk,
        "anchor_reference_arm": anchor_arm,
        "recommended_duration_sec": duration,
        "safety_rules": safety_rules,
        "review_focus": review_focus,
        "genre_profile": genre_profile,
    }


def _candidate_role(shot: dict) -> str:
    text = _shot_text(shot)
    if _has_any(text, ["hand", "finger", "touch", "hover", "puddle", "water", "glow", "reflection"]):
        if _has_any(text, ["payoff", "final", "outro", "resolution"]):
            return "high_risk_interaction_payoff"
    if _has_any(text, ["group choreography", "backup", "dancer", "dance", "confetti", "crowd"]):
        if _has_any(text, ["group choreography", "full body dance", "backup", "crowd", "confetti"]):
            return "group_choreography"
    if _has_any(text, ["guitar", "piano", "drummer", "drum", "instrument", "strum", "fingering"]):
        return "instrument_visible_hands" if _has_any(text, ["hand", "strum", "fingering", "piano"]) else "instrument_performance"
    if _has_any(text, ["release wide", "over shoulder", "over-shoulder", "world bridge", "establishing", "silhouette", "skyline", "small figure", "drive"]):
        if _has_any(text, ["payoff", "final", "outro", "resolution", "ending"]):
            return "world_bridge"
    if _has_any(text, ["motif", "symbolic", "insert", "glint", "reflection", "flare"]):
        if _has_any(text, ["release", "chorus", "payoff", "final", "outro", "resolution"]):
            return "symbolic_insert"
    if _has_any(text, ["over shoulder", "over-shoulder", "world bridge", "establishing", "silhouette", "drive"]):
        return "world_bridge"
    if _has_any(text, ["hook", "chorus", "sing", "performance", "hero face", "close-up", "closeup"]):
        return "hero_face_performance"
    if _has_any(text, ["motif", "symbolic", "insert", "glint", "reflection"]):
        return "symbolic_insert"
    return "character_medium"


def _anchor_arm(candidate_role: str) -> str:
    return {
        "hero_face_performance": "B_UPPER_ONLY",
        "character_medium": "D_FULLBODY_UPPER",
        "world_bridge": "F_FULLBODY_UPPER_WORLD",
        "symbolic_insert": "A_FULLBODY_ONLY",
        "high_risk_interaction_payoff": "D_FULLBODY_UPPER",
        "group_choreography": "D_FULLBODY_UPPER",
        "instrument_performance": "D_FULLBODY_UPPER",
        "instrument_visible_hands": "D_FULLBODY_UPPER",
    }.get(candidate_role, "D_FULLBODY_UPPER")


def _risk_class(candidate_role: str, shot: dict) -> str:
    if candidate_role == "high_risk_interaction_payoff":
        return _RED
    if candidate_role in {"group_choreography", "instrument_visible_hands"}:
        return _YELLOW
    if candidate_role in {"hero_face_performance", "world_bridge", "character_medium"}:
        return _GREEN
    return _YELLOW if candidate_role == "symbolic_insert" else _GREEN


def _recommended_duration(candidate_role: str, risk: str) -> dict:
    durations = {
        "hero_face_performance": {"min": 0.8, "max": 1.8},
        "character_medium": {"min": 0.8, "max": 2.0},
        "world_bridge": {"min": 0.8, "max": 2.0},
        "symbolic_insert": {"min": 0.3, "max": 0.8},
        "high_risk_interaction_payoff": {"min": 0.3, "max": 0.7},
        "group_choreography": {"min": 0.4, "max": 0.9},
        "instrument_performance": {"min": 0.6, "max": 1.5},
        "instrument_visible_hands": {"min": 0.3, "max": 0.8},
    }
    return durations.get(candidate_role, {"min": 0.6, "max": 1.5 if risk == _GREEN else 0.9})


def _safety_rules(candidate_role: str, risk: str) -> list[str]:
    rules = ["single_scene_integrity_required", "avoid_duplicate_protagonist"]
    if candidate_role == "high_risk_interaction_payoff":
        rules.extend(
            [
                "hover_or_reaction_alternative_required",
                "start_middle_end_review_required",
                "do_not_hold_direct_hand_contact_long",
                "generate_symbolic_insert_backup",
            ]
        )
    if candidate_role == "group_choreography":
        rules.extend(["prefer_silhouette_or_blurred_backup", "avoid_long_group_choreography_take"])
    if candidate_role in {"instrument_visible_hands", "instrument_performance"}:
        rules.extend(["prefer_hidden_or_silhouette_hands", "use_visible_playing_as_short_insert"])
    if risk != _GREEN:
        rules.append("candidate_alternative_required")
    return rules


def _review_focus(candidate_role: str, risk: str) -> list[str]:
    focus = ["identity_continuity", "outfit_preservation", "ia2v_motion_survival"]
    if candidate_role == "hero_face_performance":
        focus.extend(["face_stability", "mouth_jaw_drift"])
    if candidate_role == "world_bridge":
        focus.extend(["world_continuity", "silhouette_readability"])
    if candidate_role == "high_risk_interaction_payoff":
        focus.extend(["hand_integrity", "water_glow_contact", "reflection_drift"])
    if candidate_role == "group_choreography":
        focus.extend(["duplicate_people", "limb_coherence", "crowd_stability"])
    if candidate_role.startswith("instrument"):
        focus.extend(["hand_instrument_contact", "instrument_geometry"])
    return focus


def _genre_lane(shot: dict, style_name: str) -> str:
    explicit = str(shot.get("genre_lane", "")).strip().upper()
    if explicit:
        return explicit
    style = str(style_name or "").strip().lower()
    if style == "idol_pop":
        return "KPOP_STAGE"
    if style == "synthwave":
        return "EDM_CLUB_ABSTRACT"
    if style == "citypop":
        return "CITYPOP_DRIVE"
    return "GENERAL_MV"


def _genre_profile(genre_lane: str) -> dict:
    base = _GENRE_PROFILES.get(genre_lane, {"prefer": ["single_protagonist_performance", "symbolic_insert"], "avoid": ["dialogue_heavy_scene"]})
    return {"genre_lane": genre_lane, "prefer": list(base["prefer"]), "avoid": list(base["avoid"])}


def _genre_adds_choreo_or_instrument_risk(shot: dict, genre_profile: dict) -> bool:
    text = _shot_text(shot)
    return _has_any(
        text,
        [
            "group choreography",
            "full group",
            "backup dancer",
            "dense crowd",
            "precise guitar",
            "long visible instrument",
            "guitar fingering",
        ],
    )


def _shot_text(shot: dict) -> str:
    values = []
    for key in (
        "shot_role",
        "visual_mode",
        "section_type",
        "section_name",
        "story_function",
        "visual_event",
        "payoff_requirement",
        "genre_lane",
        "workflow_intent",
        "framing_intent",
    ):
        values.append(str(shot.get(key, "")))
    return " ".join(values).replace("_", " ").lower()


def _has_any(text: str, needles: list[str]) -> bool:
    return any(needle in text for needle in needles)


def _max_risk(left: str, right: str) -> str:
    order = {_GREEN: 0, _YELLOW: 1, _RED: 2}
    return left if order.get(left, 0) >= order.get(right, 0) else right
