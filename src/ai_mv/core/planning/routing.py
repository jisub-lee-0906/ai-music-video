from __future__ import annotations


def apply_render_routing(config: dict, shots: list[dict]) -> list[dict]:
    routed = _apply_ia2v_routing(config, shots)
    return _apply_flf2v_routing(config, routed)



def _apply_ia2v_routing(config: dict, shots: list[dict]) -> list[dict]:
    planning = config.get("planning", {}) if isinstance(config, dict) else {}
    enable_ia2v = bool(planning.get("enable_ia2v", False))
    if not enable_ia2v:
        return shots
    max_ia2v_shots = _int(planning.get("max_ia2v_shots"), 2, minimum=1)
    min_sec = _float(planning.get("ia2v_min_sec"), 4.0)
    max_sec = _float(planning.get("ia2v_max_sec"), 8.0)
    routed: list[dict] = []
    used_sections: set[int] = set()
    ia2v_count = 0
    for shot in shots:
        updated = dict(shot)
        if (
            ia2v_count < max_ia2v_shots
            and _eligible_for_ia2v(updated, min_sec, max_sec)
            and int(updated.get("source_section_index", 0) or 0) not in used_sections
        ):
            updated["render_mode"] = "ia2v"
            used_sections.add(int(updated.get("source_section_index", 0) or 0))
            ia2v_count += 1
        routed.append(updated)
    return routed



def _apply_flf2v_routing(config: dict, shots: list[dict]) -> list[dict]:
    planning = config.get("planning", {}) if isinstance(config, dict) else {}
    if not bool(planning.get("enable_flf2v", False)):
        return shots
    max_flf2v_shots = _int(planning.get("max_flf2v_shots"), 1, minimum=1)
    min_sec = _float(planning.get("flf2v_min_sec"), 3.0)
    max_sec = _float(planning.get("flf2v_max_sec"), 6.0)
    routed = [dict(shot) for shot in shots]
    flf2v_count = 0
    for idx, shot in enumerate(routed[:-1]):
        next_shot = routed[idx + 1]
        if flf2v_count >= max_flf2v_shots:
            break
        if _eligible_for_flf2v(shot, next_shot, min_sec, max_sec):
            shot["render_mode"] = "flf2v"
            shot["bridge_to_shot_id"] = next_shot["shot_id"]
            shot["shot_role"] = "bridge_transition"
            shot["visual_mode"] = "bridge_transition"
            flf2v_count += 1
    return routed



def _eligible_for_ia2v(shot: dict, min_sec: float, max_sec: float) -> bool:
    duration_sec = float(shot.get("duration_sec", 0.0) or 0.0)
    workflow_intent = str(shot.get("workflow_intent", "")).strip()
    if workflow_intent and workflow_intent != "audio_reactive_candidate":
        return False
    if str(shot.get("section_type", "")) != "chorus":
        return False
    if str(shot.get("visual_mode", "")) != "chorus_performance":
        return False
    return min_sec <= duration_sec <= max_sec



def _eligible_for_flf2v(shot: dict, next_shot: dict, min_sec: float, max_sec: float) -> bool:
    workflow_intent = str(shot.get("workflow_intent", "")).strip()
    if workflow_intent and workflow_intent != "bridge_candidate":
        return False
    duration_sec = float(shot.get("duration_sec", 0.0) or 0.0)
    if not (min_sec <= duration_sec <= max_sec):
        return False
    section_type = str(shot.get("section_type", ""))
    next_section_type = str(next_shot.get("section_type", ""))
    if section_type in {"bridge", "pre_chorus"} and next_section_type != section_type:
        return True
    return section_type == "verse" and next_section_type == "chorus" and str(shot.get("visual_mode", "")) == "window_reflection"



def _float(value: object, default: float) -> float:
    try:
        return float(value)
    except Exception:
        return default



def _int(value: object, default: int, *, minimum: int = 0) -> int:
    try:
        parsed = int(value)
    except Exception:
        return default
    return max(minimum, parsed)
