from __future__ import annotations

from ai_mv.engines.common.clip_timing import expand_anchor_clips, read_max_clip_sec
from ai_mv.core.profile_policy import resolve_profile_policy
from ai_mv.utils.text_utils import parse_target

MV_FUNCTIONS = ("establish", "coverage", "lift", "payoff", "interrupt", "residue")
KINETIC_REF_TRANSITIONS = {
    "snap_zoom_in",
    "snap_zoom_out",
    "whip_pan_left",
    "whip_pan_right",
    "crash_push_in",
    "smash_reframe",
    "strobe_jump",
    "match_cut_pose",
}


def visual_pipeline_settings(config: dict) -> dict:
    node = config.get("visual_pipeline", {}) if isinstance(config, dict) else {}
    node = node if isinstance(node, dict) else {}
    policy = resolve_profile_policy(config)
    mode = str(node.get("visual_pipeline_mode", "tti_selective_ref")).strip().lower()
    if mode not in {"tti_only", "tti_selective_ref", "tti_ref_all"}:
        mode = "tti_selective_ref"
    consistency = str(node.get("consistency_mode", "")).strip().lower()
    if consistency not in {"off", "selective", "always"}:
        consistency = "selective"
    kinetic_ref_mode = str(node.get("kinetic_ref_mode", "endpoints")).strip().lower()
    if kinetic_ref_mode not in {"all", "endpoints", "hero_only", "off"}:
        kinetic_ref_mode = "endpoints"
    hero_types = node.get("hero_shot_types", policy.get("hero_shot_types", ["EMOTION_CLOSE"]))
    sections = node.get("reference_priority_sections", policy.get("priority_sections", ["Final Chorus", "Chorus 2", "Chorus 1"]))
    location_budget = node.get("location_budget", {}) if isinstance(node.get("location_budget", {}), dict) else {}
    location_examples = node.get("location_family_examples", ["reflective threshold", "lit passage", "open night lane", "sheltered edge"])
    shot_guidance = node.get("shot_type_guidance", {}) if isinstance(node.get("shot_type_guidance", {}), dict) else {}
    grammar = node.get("mv_grammar", {}) if isinstance(node.get("mv_grammar", {}), dict) else {}
    return {
        "visual_pipeline_mode": mode,
        "consistency_mode": consistency,
        "kinetic_ref_mode": kinetic_ref_mode,
        "resolved_profile_policy": dict(policy),
        "hero_shot_types": [str(x).strip().upper() for x in hero_types if str(x).strip()],
        "reference_priority_sections": [str(x).strip().lower() for x in sections if str(x).strip()],
        "allow_face_drift_in_nonhero": bool(node.get("allow_face_drift_in_nonhero", True)),
        "location_budget": {
            "min": max(1, int(location_budget.get("min", 2))),
            "max": max(1, int(location_budget.get("max", 3))),
        },
        "location_family_examples": [str(x).strip() for x in location_examples if str(x).strip()],
        "shot_type_guidance": {
            str(key).strip().lower(): [str(x).strip().upper() for x in value if str(x).strip()]
            for key, value in shot_guidance.items()
            if str(key).strip() and isinstance(value, list)
        },
        "mv_grammar": {
            "verse_coverage_bias": str(grammar.get("verse_coverage_bias", "travel coverage")).strip(),
            "chorus_payoff_bias": str(grammar.get("chorus_payoff_bias", "clear hero payoff")).strip(),
            "bridge_interrupt_bias": str(grammar.get("bridge_interrupt_bias", "interrupted isolation")).strip(),
            "outro_residue_bias": str(grammar.get("outro_residue_bias", "residue image")).strip(),
        },
    }


def shot_type_guidance_digest(config: dict) -> str:
    settings = visual_pipeline_settings(config)
    guidance = settings.get("shot_type_guidance", {})
    order = ["intro", "verse", "pre_chorus", "chorus", "post_chorus", "bridge", "outro"]
    rows: list[str] = []
    for key in order:
        vals = guidance.get(key, [])
        if vals:
            rows.append(f"{key}={','.join(vals)}")
    return "; ".join(rows)


def location_grammar_digest(config: dict) -> str:
    settings = visual_pipeline_settings(config)
    budget = settings.get("location_budget", {"min": 2, "max": 3})
    examples = settings.get("location_family_examples", [])
    return (
        f"budget={budget.get('min', 2)}-{budget.get('max', 3)} recurring families; "
        f"examples={', '.join(examples)}"
    )


def build_mv_directives(config: dict) -> dict:
    mv = config.get("mv", {}) if isinstance(config, dict) else {}
    mv = mv if isinstance(mv, dict) else {}
    return {
        "motif_seed": str(mv.get("story_world", "")).strip(),
        "chorus_payoff_hint": str(mv.get("payoff_style", "")).strip(),
        "bridge_interrupt_hint": str(mv.get("action_vocabulary", "")).strip(),
        "outro_residue_hint": str(mv.get("outro_feel", "")).strip(),
    }


def build_section_semantics(config: dict, sections: list[dict]) -> list[dict]:
    settings = visual_pipeline_settings(config)
    out: list[dict] = []
    for row in sections:
        section_name = str(row.get("name", "section")).strip().lower()
        section_label = str(row.get("label", row.get("name", "section"))).strip()
        out.append(
            {
                "section_name": section_name,
                "section_label": section_label,
                "energy_phase": _energy_phase(section_name, section_label),
                "release_level": _release_level(section_name, section_label),
                "hook_priority": _hook_priority(section_name, section_label),
                "movement_bias": _movement_bias(settings["mv_grammar"], section_name, section_label),
                "return_weight": _return_weight(section_name, section_label),
                "hero_frame_priority": _hero_frame_priority(section_name, section_label),
            }
        )
    return out


def section_semantics_digest(audio_map: dict, limit: int = 12) -> str:
    rows = audio_map.get("section_semantics", []) if isinstance(audio_map, dict) else []
    out: list[str] = []
    for row in rows[: max(1, limit)]:
        if not isinstance(row, dict):
            continue
        out.append(
            f"{row.get('section_label', row.get('section_name', 'section'))}|"
            f"{row.get('mv_function', row.get('movement_bias', ''))}|"
            f"{row.get('release_level', '')}|"
            f"{row.get('hero_frame_priority', '')}"
        )
    return ", ".join(x for x in out if x)


def attach_tti_metadata(shot: dict, section_name: str, section_label: str) -> dict:
    item = dict(shot)
    mv_function = _mv_function(section_name, section_label)
    hero_frame_score = _hero_frame_score(section_name, section_label, str(item.get("shot_type", "")))
    shot_priority = _shot_priority(mv_function, hero_frame_score)
    item["hero_frame_score"] = hero_frame_score
    item["consistency_need"] = _consistency_need(hero_frame_score, str(item.get("shot_type", "")))
    item["mv_function"] = mv_function
    item["return_weight"] = _return_weight(section_name, section_label)
    item["edit_density"] = _edit_density(mv_function)
    item["shot_priority"] = shot_priority
    item["transition_role"] = _transition_role(mv_function, shot_priority)
    return item


def build_clip_routes(config: dict, anchors: list[dict]) -> list[dict]:
    fps = parse_target(config.get("video", {}).get("target", "1920x1080@24"))[2]
    clip_anchors = expand_anchor_clips(anchors, fps, read_max_clip_sec(config))
    routes: list[dict] = []
    for anchor in clip_anchors:
        item = dict(anchor)
        item["clip_phase"] = _clip_phase(anchor)
        use_ref, reason = should_use_ref(anchor, config)
        item["use_ref"] = bool(use_ref)
        item["route_reason"] = reason
        routes.append(item)
    return routes


def should_use_ref(shot: dict, config: dict) -> tuple[bool, str]:
    settings = visual_pipeline_settings(config)
    mode = settings["visual_pipeline_mode"]
    consistency = settings["consistency_mode"]
    policy = settings.get("resolved_profile_policy", {})
    if mode == "tti_only" or consistency == "off":
        return False, "tti_only coverage-first mode"
    if mode == "tti_ref_all" or consistency == "always":
        return True, "always-on reference consistency"
    label = str(shot.get("section_label", shot.get("section_name", ""))).strip().lower()
    shot_type = str(shot.get("shot_type", "")).strip().upper()
    hero_score = int(shot.get("hero_frame_score", 1))
    consistency_need = str(shot.get("consistency_need", "low")).strip().lower()
    phase = _clip_phase(shot)
    mv_function = str(shot.get("mv_function", "")).strip().lower()
    kinetic_transition = str(shot.get("kinetic_transition", "")).strip().lower()
    kinetic_intensity = str(shot.get("kinetic_intensity", "")).strip().lower()
    face_exposure = str(shot.get("face_exposure_level", "")).strip().lower() or _default_face_exposure(shot_type, mv_function)
    continuity_priority = str(shot.get("continuity_priority", "")).strip().lower()
    wardrobe_read = str(shot.get("wardrobe_read", "")).strip().lower()
    ref_triggers = policy.get("ref_triggers", {}) if isinstance(policy, dict) else {}
    direct_face_sections = {str(x).strip().lower() for x in policy.get("direct_face_sections", [])} if isinstance(policy, dict) else set()
    is_priority_section = any(ref in label for ref in settings["reference_priority_sections"])
    if bool(ref_triggers.get("face_sensitive", True)) and face_exposure in {"direct", "soft"} and phase != "advance":
        return True, "identity-sensitive face shot"
    if continuity_priority == "high" and phase in {"single", "establish", "resolve"}:
        return True, "high continuity anchor"
    if bool(ref_triggers.get("wardrobe_read_high", False)) and wardrobe_read == "high" and phase in {"single", "establish"} and hero_score >= 2:
        return True, "wardrobe continuity anchor"
    if direct_face_sections and label in direct_face_sections and face_exposure in {"direct", "soft"}:
        return True, "policy direct-face section"
    if kinetic_transition in KINETIC_REF_TRANSITIONS:
        kinetic_ref = _kinetic_ref_decision(
            settings["kinetic_ref_mode"],
            shot_type,
            hero_score,
            consistency_need,
            phase,
            mv_function,
            kinetic_intensity,
            is_priority_section,
            settings["hero_shot_types"],
        )
        if kinetic_ref is not None:
            return kinetic_ref
    if kinetic_intensity in {"high", "max"} and phase in {"establish", "resolve"}:
        return True, "high kinetic endpoint lock"
    if is_priority_section and bool(ref_triggers.get("payoff_sections", True)):
        if hero_score >= 4:
            return True, "priority return hero"
        if hero_score >= 3 and phase in {"establish", "resolve"}:
            return True, f"priority return {phase}"
    if shot_type in set(settings["hero_shot_types"]) and consistency_need in {"normal", "high"}:
        return True, "hero shot type"
    if mv_function in {"interrupt", "payoff"} and consistency_need == "high" and phase != "advance":
        return True, f"{mv_function} identity hold"
    if consistency_need == "high" and not settings["allow_face_drift_in_nonhero"]:
        return True, "high identity lock"
    return False, "tti-only coverage shot"


def _kinetic_ref_decision(
    kinetic_ref_mode: str,
    shot_type: str,
    hero_score: int,
    consistency_need: str,
    phase: str,
    mv_function: str,
    kinetic_intensity: str,
    is_priority_section: bool,
    hero_shot_types: list[str],
) -> tuple[bool, str] | None:
    is_hero_type = shot_type in set(hero_shot_types)
    if kinetic_ref_mode == "off":
        return None
    if kinetic_ref_mode == "all":
        return True, "kinetic transition anchor"
    if is_hero_type or consistency_need == "high" or hero_score >= 4:
        return True, "kinetic hero anchor"
    if kinetic_ref_mode == "hero_only":
        return None
    if phase in {"establish", "resolve"} and (
        is_priority_section or mv_function in {"payoff", "interrupt"} or kinetic_intensity in {"high", "max"} or hero_score >= 3
    ):
        return True, "kinetic endpoint lock"
    return None


def _default_face_exposure(shot_type: str, mv_function: str) -> str:
    shot = str(shot_type).strip().upper()
    fn = str(mv_function).strip().lower()
    if shot == "DETAIL_INSERT":
        return "hidden"
    if shot == "ENV_TRANSITION":
        return "partial"
    if shot == "EMOTION_CLOSE":
        return "direct" if fn == "payoff" else "soft"
    if shot == "CHAR_MASTER":
        return "soft"
    return "partial"


def route_summary(routes: list[dict]) -> list[dict]:
    out: list[dict] = []
    for row in routes:
        out.append(
            {
                "shot_id": str(row.get("shot_id", "")),
                "lyric_beat_id": str(row.get("lyric_beat_id", "")),
                "use_ref": bool(row.get("use_ref", False)),
                "reason": str(row.get("route_reason", "")),
                "mv_function": str(row.get("mv_function", "")),
                "clip_phase": str(row.get("clip_phase", "")),
                "shot_priority": str(row.get("shot_priority", "")),
                "hero_frame_score": int(row.get("hero_frame_score", 0)),
                "consistency_need": str(row.get("consistency_need", "")),
                "kinetic_transition": str(row.get("kinetic_transition", "")),
                "kinetic_intensity": str(row.get("kinetic_intensity", "")),
            }
        )
    return out


def _energy_phase(section_name: str, section_label: str) -> str:
    sec = str(section_name).strip().lower()
    label = str(section_label).strip().lower()
    if "final chorus" in label:
        return "arrival"
    mapping = {
        "intro": "set",
        "verse_1": "contained",
        "verse_2": "contained",
        "pre_chorus": "lift",
        "chorus": "release",
        "post_chorus": "echo",
        "bridge": "break",
        "outro": "settle",
    }
    return mapping.get(sec, "contained")


def _release_level(section_name: str, section_label: str) -> str:
    sec = str(section_name).strip().lower()
    label = str(section_label).strip().lower()
    if "final chorus" in label:
        return "peak"
    if "chorus 2" in label:
        return "high"
    if sec == "chorus":
        return "high"
    if sec == "pre_chorus":
        return "medium"
    if sec == "bridge":
        return "withheld"
    if sec == "outro":
        return "settled"
    return "low"


def _hook_priority(section_name: str, section_label: str) -> str:
    sec = str(section_name).strip().lower()
    label = str(section_label).strip().lower()
    if "final chorus" in label:
        return "peak"
    if sec == "chorus":
        return "high"
    if sec == "pre_chorus":
        return "medium"
    return "low"


def _movement_bias(grammar: dict, section_name: str, section_label: str) -> str:
    sec = str(section_name).strip().lower()
    label = str(section_label).strip().lower()
    if "final chorus" in label or sec == "chorus":
        return str(grammar.get("chorus_payoff_bias", "")).strip()
    if sec == "bridge":
        return str(grammar.get("bridge_interrupt_bias", "")).strip()
    if sec == "outro":
        return str(grammar.get("outro_residue_bias", "")).strip()
    return str(grammar.get("verse_coverage_bias", "")).strip()


def _hero_frame_priority(section_name: str, section_label: str) -> str:
    sec = str(section_name).strip().lower()
    label = str(section_label).strip().lower()
    if "final chorus" in label:
        return "peak"
    if sec == "chorus":
        return "high"
    if sec == "pre_chorus":
        return "medium"
    if sec == "bridge":
        return "medium"
    return "low"


def _return_weight(section_name: str, section_label: str) -> int:
    sec = str(section_name).strip().lower()
    label = str(section_label).strip().lower()
    if "final chorus" in label:
        return 4
    if "chorus 2" in label:
        return 3
    if sec == "chorus":
        return 2
    if sec == "bridge":
        return 2
    return 1


def _mv_function(section_name: str, section_label: str) -> str:
    sec = str(section_name).strip().lower()
    label = str(section_label).strip().lower()
    if sec == "intro":
        return "establish"
    if sec in {"verse_1", "verse_2"}:
        return "coverage"
    if sec == "pre_chorus":
        return "lift"
    if sec == "chorus" and "final chorus" in label:
        return "payoff"
    if sec == "chorus":
        return "payoff"
    if sec == "bridge":
        return "interrupt"
    if sec == "outro":
        return "residue"
    return "coverage"


def _hero_frame_score(section_name: str, section_label: str, shot_type: str) -> int:
    sec = str(section_name).strip().lower()
    label = str(section_label).strip().lower()
    shot = str(shot_type).strip().upper()
    score = 1
    if shot == "EMOTION_CLOSE":
        score += 2
    elif shot == "CHAR_MASTER":
        score += 1
    if sec == "pre_chorus":
        score += 1
    if sec == "chorus":
        score += 1
    if "final chorus" in label:
        score += 1
    return max(1, min(5, score))


def _consistency_need(hero_frame_score: int, shot_type: str) -> str:
    shot = str(shot_type).strip().upper()
    if hero_frame_score >= 4 or shot == "EMOTION_CLOSE":
        return "high"
    if hero_frame_score >= 3 or shot == "CHAR_MASTER":
        return "normal"
    return "low"


def _edit_density(mv_function: str) -> str:
    mapping = {
        "establish": "low",
        "coverage": "medium",
        "lift": "medium",
        "payoff": "high",
        "interrupt": "sparse",
        "residue": "low",
    }
    return mapping.get(str(mv_function).strip().lower(), "medium")


def _shot_priority(mv_function: str, hero_frame_score: int) -> str:
    fn = str(mv_function).strip().lower()
    if fn == "payoff" and hero_frame_score >= 3:
        return "hero"
    if fn in {"interrupt", "lift"} and hero_frame_score >= 3:
        return "accent"
    if fn in {"establish", "residue"}:
        return "anchor"
    return "support"


def _transition_role(mv_function: str, shot_priority: str) -> str:
    fn = str(mv_function).strip().lower()
    pri = str(shot_priority).strip().lower()
    if fn == "establish":
        return "entry"
    if fn == "residue":
        return "exit"
    if fn == "interrupt":
        return "break"
    if pri == "hero":
        return "arrival"
    if fn == "lift":
        return "build"
    return "carry"


def _clip_phase(shot: dict) -> str:
    index = int(shot.get("clip_index", 1))
    count = int(shot.get("clip_count", 1))
    if count <= 1:
        return "single"
    if index <= 1:
        return "establish"
    if index >= count:
        return "resolve"
    return "advance"
