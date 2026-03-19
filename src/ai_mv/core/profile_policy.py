from __future__ import annotations


_VISUAL_MODES = {"character_heavy", "balanced", "environment_first"}
_CONTINUITY_MODES = {"same_heroine", "same_persona", "motif_first"}
_FACE_POLICIES = {"frequent", "selective", "payoff_only", "avoid"}
_SHOT_BIASES = {"performance", "environment", "object_symbol", "mixed"}
_REF_POLICIES = {"broad", "endpoints", "identity_sensitive_only", "minimal"}
_DENSITIES = {"low", "medium", "high"}
_GEOGRAPHY_MODES = {"recurring_families", "free_drift_forbidden"}
_ANCHOR_MODES = {"master_only", "shot_anchor_required"}
_VISUAL_MV_MODES = {"character_narrative", "symbolic_edit", "bga_event"}
_SUBJECT_EXPOSURES = {"high", "selective", "low"}
_PAYOFF_MODES = {"face_peak", "motif_peak", "system_peak"}


def resolve_profile_policy(config: dict) -> dict:
    raw = config.get("visual_policy", {}) if isinstance(config, dict) else {}
    raw = raw if isinstance(raw, dict) else {}
    visual = config.get("visual", {}) if isinstance(config, dict) else {}
    visual = visual if isinstance(visual, dict) else {}
    mv = config.get("mv", {}) if isinstance(config, dict) else {}
    mv = mv if isinstance(mv, dict) else {}
    visual_text = str(visual.get("brief", "")).strip().lower()
    world_text = str(mv.get("story_world", "")).strip().lower()
    payoff_text = str(mv.get("payoff_style", "")).strip().lower()

    visual_mode = _enum(raw.get("visual_mode"), _VISUAL_MODES, _derive_visual_mode(visual_text))
    continuity_mode = _enum(raw.get("continuity_mode"), _CONTINUITY_MODES, _derive_continuity_mode(world_text))
    face_policy = _enum(raw.get("face_policy"), _FACE_POLICIES, _derive_face_policy(visual_text, payoff_text, visual_mode))
    shot_bias = _enum(raw.get("shot_bias"), _SHOT_BIASES, _derive_shot_bias(visual_mode, visual_text))
    ref_policy = _enum(raw.get("ref_policy"), _REF_POLICIES, _derive_ref_policy(face_policy, continuity_mode))
    closeup_density = _enum(raw.get("closeup_density"), _DENSITIES, _derive_closeup_density(face_policy))
    motion_density = _enum(raw.get("motion_density"), _DENSITIES, _derive_motion_density(visual_text))
    geography_mode = _enum(raw.get("geography_mode"), _GEOGRAPHY_MODES, "recurring_families")
    anchor_mode = _enum(raw.get("anchor_mode"), _ANCHOR_MODES, "shot_anchor_required")
    visual_mv_mode = _enum(raw.get("visual_mv_mode"), _VISUAL_MV_MODES, _derive_visual_mv_mode(visual_text, shot_bias))
    subject_exposure = _enum(raw.get("subject_exposure"), _SUBJECT_EXPOSURES, _derive_subject_exposure(face_policy, visual_mode))
    motif_density = _enum(raw.get("motif_density"), _DENSITIES, _derive_motif_density(visual_text, shot_bias))
    graphic_event_density = _enum(raw.get("graphic_event_density"), _DENSITIES, _derive_graphic_event_density(visual_text))
    environment_event_density = _enum(raw.get("environment_event_density"), _DENSITIES, _derive_environment_event_density(visual_mode, shot_bias))
    visual_payoff_mode = _enum(raw.get("visual_payoff_mode"), _PAYOFF_MODES, _derive_visual_payoff_mode(face_policy, visual_mode, visual_text))
    direct_face_sections = _str_list(raw.get("direct_face_sections", [])) or _default_direct_face_sections(face_policy)
    priority_sections = _str_list(raw.get("priority_sections", [])) or ["Final Chorus", "Chorus 2", "Chorus 1"]
    hero_shot_types = _str_list(raw.get("hero_shot_types", []), upper=True) or _default_hero_shot_types(face_policy, visual_mode)
    max_direct_face_ratio = _float(raw.get("max_direct_face_ratio"), _default_max_direct_face_ratio(face_policy))
    reflection_usage = _derive_reflection_usage(visual_mv_mode, shot_bias, visual_text)
    palette_bias = _derive_palette_bias(visual_text, world_text)
    motif_families = _derive_motif_families(visual_text, world_text)
    preferred_composition_families = _preferred_composition_families(visual_mv_mode)
    disfavored_composition_families = _disfavored_composition_families()

    return {
        "visual_mode": visual_mode,
        "continuity_mode": continuity_mode,
        "face_policy": face_policy,
        "shot_bias": shot_bias,
        "ref_policy": ref_policy,
        "closeup_density": closeup_density,
        "motion_density": motion_density,
        "geography_mode": geography_mode,
        "anchor_mode": anchor_mode,
        "visual_mv_mode": visual_mv_mode,
        "subject_exposure": subject_exposure,
        "motif_density": motif_density,
        "graphic_event_density": graphic_event_density,
        "environment_event_density": environment_event_density,
        "visual_payoff_mode": visual_payoff_mode,
        "direct_face_sections": direct_face_sections,
        "priority_sections": priority_sections,
        "hero_shot_types": hero_shot_types,
        "max_direct_face_ratio": max(0.0, min(1.0, max_direct_face_ratio)),
        "reflection_usage": reflection_usage,
        "palette_bias": palette_bias,
        "motif_families": motif_families,
        "preferred_composition_families": preferred_composition_families,
        "disfavored_composition_families": disfavored_composition_families,
        "shot_distribution": _shot_distribution(visual_mode, shot_bias, face_policy, visual_mv_mode),
        "face_exposure_defaults": _face_exposure_defaults(face_policy),
        "ref_triggers": _ref_triggers(ref_policy),
    }


def _derive_visual_mode(visual_text: str) -> str:
    text = str(visual_text).lower()
    if any(token in text for token in ("extreme close-up", "camera-ready face", "direct stare", "eye lock", "glam impact")):
        return "character_heavy"
    if any(token in text for token in ("thresholds", "passages", "lanes", "corridors", "floors", "corridor", "world")):
        return "balanced"
    return "balanced"


def _derive_continuity_mode(world_text: str) -> str:
    text = str(world_text).lower()
    if "same heroine" in text:
        return "same_heroine"
    if "same" in text:
        return "same_persona"
    return "same_persona"


def _derive_face_policy(visual_text: str, payoff_text: str, visual_mode: str) -> str:
    visual = str(visual_text).lower()
    payoff = str(payoff_text).lower()
    if "one extreme close-up" in payoff:
        return "payoff_only"
    if "selective extreme close-up" in visual or "selective extreme close-ups" in visual:
        return "selective"
    if "extreme close-up" in visual or "direct stare" in visual or "eye lock" in visual:
        return "selective" if visual_mode != "character_heavy" else "frequent"
    return "avoid" if visual_mode == "environment_first" else "selective"


def _derive_shot_bias(visual_mode: str, visual_text: str) -> str:
    text = str(visual_text).lower()
    if any(token in text for token in ("object", "prop", "detail", "motif")):
        return "object_symbol"
    if visual_mode == "environment_first":
        return "environment"
    if any(token in text for token in ("performance", "pose", "stare", "center")):
        return "performance"
    return "mixed"


def _derive_ref_policy(face_policy: str, continuity_mode: str) -> str:
    if continuity_mode == "same_heroine":
        if face_policy in {"frequent", "selective"}:
            return "identity_sensitive_only"
        return "endpoints"
    if continuity_mode == "motif_first":
        return "minimal"
    return "endpoints"


def _derive_closeup_density(face_policy: str) -> str:
    return {
        "frequent": "high",
        "selective": "medium",
        "payoff_only": "low",
        "avoid": "low",
    }.get(face_policy, "medium")


def _derive_motion_density(visual_text: str) -> str:
    text = str(visual_text).lower()
    if any(token in text for token in ("maximum kinetic", "hard-cut", "smash reframe", "strobe hits", "whip pan", "snap zoom")):
        return "high"
    if "restrained" in text or "poised stillness" in text:
        return "medium"
    return "medium"


def _derive_visual_mv_mode(visual_text: str, shot_bias: str) -> str:
    text = str(visual_text).lower()
    if any(token in text for token in ("match-cut", "strobe", "graphic", "silhouette", "symbolic", "surreal")):
        return "bga_event"
    if shot_bias in {"environment", "object_symbol"}:
        return "symbolic_edit"
    return "character_narrative"


def _derive_subject_exposure(face_policy: str, visual_mode: str) -> str:
    if face_policy == "frequent":
        return "high"
    if face_policy == "avoid" or visual_mode == "environment_first":
        return "low"
    return "selective"


def _derive_motif_density(visual_text: str, shot_bias: str) -> str:
    text = str(visual_text).lower()
    if shot_bias == "object_symbol" or any(token in text for token in ("motif", "symbol", "reflection", "threshold", "ritual", "silhouette")):
        return "high"
    if shot_bias == "environment":
        return "medium"
    return "low"


def _derive_graphic_event_density(visual_text: str) -> str:
    text = str(visual_text).lower()
    if any(token in text for token in ("strobe", "match-cut", "snap zoom", "graphic", "silhouette", "glitch", "motion-blur residue")):
        return "high"
    if any(token in text for token in ("whip pan", "dynamic shadows", "high-contrast")):
        return "medium"
    return "low"


def _derive_environment_event_density(visual_mode: str, shot_bias: str) -> str:
    if visual_mode == "environment_first" or shot_bias == "environment":
        return "high"
    if shot_bias == "mixed":
        return "medium"
    return "low"


def _derive_visual_payoff_mode(face_policy: str, visual_mode: str, visual_text: str) -> str:
    text = str(visual_text).lower()
    if any(token in text for token in ("system", "world", "threshold", "reflection", "lane", "space")):
        return "system_peak"
    if face_policy in {"frequent", "selective"} and visual_mode == "character_heavy":
        return "face_peak"
    return "motif_peak"


def _derive_reflection_usage(visual_mv_mode: str, shot_bias: str, visual_text: str) -> str:
    text = str(visual_text).lower()
    if "reflection" in text or "mirror" in text:
        return "selected_only" if visual_mv_mode in {"symbolic_edit", "bga_event"} else "allowed"
    if shot_bias == "object_symbol":
        return "selected_only"
    return "minimal"


def _derive_palette_bias(visual_text: str, world_text: str) -> str:
    text = f"{visual_text} {world_text}".lower()
    if any(token in text for token in ("city pop", "city-pop", "retro", "late-night city")):
        return "retro_pop_neon"
    if any(token in text for token in ("cyber", "neon", "glitch")):
        return "cyber_pop_high_contrast"
    return "graphic_pop"


def _derive_motif_families(visual_text: str, world_text: str) -> list[str]:
    text = f"{visual_text} {world_text}".lower()
    if any(token in text for token in ("city pop", "city-pop", "late-night city", "lane", "threshold", "passage")):
        return [
            "train window",
            "curb edge",
            "puddle ring",
            "umbrella tip",
            "ticket gate",
            "vending glow",
            "phone light",
            "rail shadow",
        ]
    return [
        "threshold edge",
        "reflection surface",
        "light smear",
        "street token",
        "small object insert",
    ]


def _preferred_composition_families(visual_mv_mode: str) -> list[str]:
    if visual_mv_mode == "bga_event":
        return [
            "asymmetrical poster crop",
            "low horizon silhouette",
            "floating object field",
            "isolated small figure",
            "offset silhouette crop",
            "sticker-cluster layout",
        ]
    if visual_mv_mode == "symbolic_edit":
        return [
            "asymmetrical poster crop",
            "isolated small figure",
            "floating object field",
            "offset silhouette crop",
        ]
    return ["poster close crop", "low horizon silhouette", "offset silhouette crop"]


def _disfavored_composition_families() -> list[str]:
    return ["split reflection diptych", "centered two-body", "bilateral symmetry", "mirrored-face split"]


def _default_direct_face_sections(face_policy: str) -> list[str]:
    if face_policy == "frequent":
        return ["Chorus 1", "Chorus 2", "Final Chorus"]
    if face_policy in {"selective", "payoff_only"}:
        return ["Final Chorus"]
    return []


def _default_hero_shot_types(face_policy: str, visual_mode: str) -> list[str]:
    if face_policy == "avoid" and visual_mode == "environment_first":
        return ["CHAR_MASTER"]
    return ["EMOTION_CLOSE", "CHAR_MASTER"]


def _default_max_direct_face_ratio(face_policy: str) -> float:
    return {
        "frequent": 0.35,
        "selective": 0.2,
        "payoff_only": 0.12,
        "avoid": 0.05,
    }.get(face_policy, 0.2)


def _shot_distribution(visual_mode: str, shot_bias: str, face_policy: str, visual_mv_mode: str) -> dict[str, float]:
    base = {
        "CHAR_MASTER": 0.18,
        "EMOTION_CLOSE": 0.18,
        "PERF_WIDE": 0.28,
        "ENV_TRANSITION": 0.22,
        "DETAIL_INSERT": 0.14,
    }
    if visual_mv_mode == "symbolic_edit":
        base = {
            "CHAR_MASTER": 0.08,
            "EMOTION_CLOSE": 0.08,
            "PERF_WIDE": 0.18,
            "ENV_TRANSITION": 0.18,
            "DETAIL_INSERT": 0.12,
            "SYMBOLIC_INSERT": 0.14,
            "GRAPHIC_EVENT": 0.10,
            "WORLD_EVENT": 0.08,
            "TRANSITIONAL_ABSTRACT": 0.02,
            "RHYTHM_DETAIL": 0.02,
        }
    elif visual_mv_mode == "bga_event":
        base = {
            "CHAR_MASTER": 0.04,
            "EMOTION_CLOSE": 0.04,
            "PERF_WIDE": 0.12,
            "ENV_TRANSITION": 0.14,
            "DETAIL_INSERT": 0.10,
            "SYMBOLIC_INSERT": 0.18,
            "GRAPHIC_EVENT": 0.16,
            "WORLD_EVENT": 0.12,
            "TRANSITIONAL_ABSTRACT": 0.06,
            "RHYTHM_DETAIL": 0.04,
        }
    if visual_mode == "environment_first":
        base = {"CHAR_MASTER": 0.08, "EMOTION_CLOSE": 0.08, "PERF_WIDE": 0.24, "ENV_TRANSITION": 0.36, "DETAIL_INSERT": 0.24}
    elif visual_mode == "character_heavy":
        base = {"CHAR_MASTER": 0.22, "EMOTION_CLOSE": 0.26, "PERF_WIDE": 0.26, "ENV_TRANSITION": 0.16, "DETAIL_INSERT": 0.10}
        if visual_mv_mode in {"symbolic_edit", "bga_event"}:
            base["SYMBOLIC_INSERT"] = 0.08
            base["GRAPHIC_EVENT"] = 0.08
            base["WORLD_EVENT"] = 0.06
            base["DETAIL_INSERT"] = max(0.06, base["DETAIL_INSERT"] - 0.04)
            base["CHAR_MASTER"] = max(0.14, base["CHAR_MASTER"] - 0.06)
            base["EMOTION_CLOSE"] = max(0.18, base["EMOTION_CLOSE"] - 0.06)
    if shot_bias == "environment":
        base["ENV_TRANSITION"] += 0.08
        base["EMOTION_CLOSE"] -= 0.05
        base["CHAR_MASTER"] -= 0.03
    elif shot_bias == "object_symbol":
        if visual_mv_mode in {"symbolic_edit", "bga_event"}:
            base["SYMBOLIC_INSERT"] = base.get("SYMBOLIC_INSERT", 0.0) + 0.08
            base["GRAPHIC_EVENT"] = base.get("GRAPHIC_EVENT", 0.0) + 0.05
            base["WORLD_EVENT"] = base.get("WORLD_EVENT", 0.0) + 0.03
            base["DETAIL_INSERT"] = max(0.06, base.get("DETAIL_INSERT", 0.0) - 0.03)
            base["EMOTION_CLOSE"] = max(0.03, base.get("EMOTION_CLOSE", 0.0) - 0.07)
            base["CHAR_MASTER"] = max(0.03, base.get("CHAR_MASTER", 0.0) - 0.06)
        else:
            base["DETAIL_INSERT"] += 0.10
            base["EMOTION_CLOSE"] -= 0.05
            base["CHAR_MASTER"] -= 0.05
    elif shot_bias == "performance":
        base["PERF_WIDE"] += 0.06
        base["CHAR_MASTER"] += 0.03
        base["ENV_TRANSITION"] -= 0.04
        base["DETAIL_INSERT"] -= 0.05
    if face_policy == "avoid":
        base["EMOTION_CLOSE"] = max(0.04, base["EMOTION_CLOSE"] - 0.08)
        base["ENV_TRANSITION"] += 0.04
        base["DETAIL_INSERT"] += 0.04
        if visual_mv_mode in {"symbolic_edit", "bga_event"}:
            base["SYMBOLIC_INSERT"] = base.get("SYMBOLIC_INSERT", 0.0) + 0.04
            base["WORLD_EVENT"] = base.get("WORLD_EVENT", 0.0) + 0.02
    elif face_policy == "frequent":
        base["EMOTION_CLOSE"] += 0.06
        base["DETAIL_INSERT"] = max(0.06, base["DETAIL_INSERT"] - 0.03)
        base["ENV_TRANSITION"] = max(0.10, base["ENV_TRANSITION"] - 0.03)
    total = sum(base.values()) or 1.0
    return {key: round(val / total, 3) for key, val in base.items()}


def _face_exposure_defaults(face_policy: str) -> dict[str, str]:
    emotion_close = {
        "frequent": "direct",
        "selective": "soft",
        "payoff_only": "soft",
        "avoid": "partial",
    }.get(face_policy, "soft")
    return {
        "CHAR_MASTER": "soft" if face_policy != "avoid" else "partial",
        "EMOTION_CLOSE": emotion_close,
        "PERF_WIDE": "partial",
        "ENV_TRANSITION": "partial",
        "DETAIL_INSERT": "hidden",
    }


def _ref_triggers(ref_policy: str) -> dict[str, bool]:
    if ref_policy == "broad":
        return {"face_sensitive": True, "payoff_sections": True, "section_entry_return": True, "wardrobe_read_high": True}
    if ref_policy == "identity_sensitive_only":
        return {"face_sensitive": True, "payoff_sections": True, "section_entry_return": False, "wardrobe_read_high": True}
    if ref_policy == "endpoints":
        return {"face_sensitive": True, "payoff_sections": True, "section_entry_return": True, "wardrobe_read_high": False}
    return {"face_sensitive": True, "payoff_sections": False, "section_entry_return": False, "wardrobe_read_high": False}


def _enum(value: object, allowed: set[str], default: str) -> str:
    text = str(value).strip().lower()
    return text if text in allowed else default


def _str_list(raw: object, upper: bool = False) -> list[str]:
    if not isinstance(raw, list):
        return []
    out = []
    for item in raw:
        text = str(item).strip()
        if not text:
            continue
        out.append(text.upper() if upper else text)
    return out


def _float(value: object, default: float) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)
