from __future__ import annotations

from ai_mv.engines.common.clip_timing import expand_anchor_clips, read_max_clip_sec
from ai_mv.utils.text_utils import parse_target
from ai_mv.core.visual_pipeline_settings import visual_pipeline_settings

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
    anchor_strategy = str(shot.get("anchor_strategy", "")).strip().lower()
    continuity_basis = str(shot.get("continuity_basis", "")).strip().lower()
    wardrobe_read = str(shot.get("wardrobe_read", "")).strip().lower()
    ref_triggers = policy.get("ref_triggers", {}) if isinstance(policy, dict) else {}
    direct_face_sections = {str(x).strip().lower() for x in policy.get("direct_face_sections", [])} if isinstance(policy, dict) else set()
    is_priority_section = any(ref in label for ref in settings["reference_priority_sections"])
    if anchor_strategy == "refine_anchor" and continuity_basis in {"heroine", "motif", "world"} and phase != "advance":
        return True, f"refine anchor for {continuity_basis} continuity"
    if anchor_strategy == "reuse_anchor" and continuity_basis in {"none", "motif"} and face_exposure not in {"direct", "soft"}:
        return False, "reuse anchor hold beat"
    if anchor_strategy == "new_anchor" and continuity_priority != "high" and face_exposure not in {"direct", "soft"} and not is_priority_section:
        return False, "new anchor scene change"
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
    if shot in {"DETAIL_INSERT", "SYMBOLIC_INSERT", "RHYTHM_DETAIL"}:
        return "hidden"
    if shot in {"ENV_TRANSITION", "WORLD_EVENT", "TRANSITIONAL_ABSTRACT", "GRAPHIC_EVENT"}:
        return "partial"
    if shot == "EMOTION_CLOSE":
        return "direct" if fn == "payoff" else "soft"
    if shot == "CHAR_MASTER":
        return "soft"
    return "partial"


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
