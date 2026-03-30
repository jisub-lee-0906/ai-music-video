from __future__ import annotations

from ai_mv.core.contracts.stage_io import StageInput, StageOutput
from ai_mv.core.director_brief import build_director_brief_intent
from ai_mv.core.stages.payload_views import merge_planner_prompt
from ai_mv.engines.flux_2_dev_ref.runner import run_flux2_ref


def run_flux2_ref_chain_v2(stage_input: StageInput) -> StageOutput:
    plan = build_flux2_ref_plan_v2(stage_input.config, stage_input.payload)
    flux2_ref_images = run_flux2_ref(stage_input.config, plan) if plan["items"] else []
    clip_routes = _clip_routes_from_v2(stage_input.payload, flux2_ref_images)
    workflow_v2 = dict(stage_input.payload.get("workflow_inputs_v2", {}))
    workflow_v2["flux2_ref_chain_v2"] = {
        "item_count": len(plan["items"]),
        "items": [
            {"shot_id": str(item["shot_id"]), "prompt_text": str(item["prompt_text"])}
            for item in plan["items"]
        ],
    }
    return StageOutput(
        "flux2_ref_chain_v2",
        "done",
        {
            "flux2_ref_images": flux2_ref_images,
            "clip_routes": clip_routes,
            "workflow_inputs_v2": workflow_v2,
            "planner_prompts": merge_planner_prompt(
                stage_input.payload,
                "flux2_ref_chain_v2",
                {"prompt": "Render scene-specific Flux2 reference start/end images from the v2 director plan while preserving the same heroine."},
            ),
        },
        [],
    )


def build_flux2_ref_plan_v2(config: dict, payload: dict) -> dict:
    brief = build_director_brief_intent(config)
    shots = [row for row in payload.get("render_plan_v2", {}).get("shot_packages", []) if isinstance(row, dict)]
    master_anchor = str(payload.get("master_anchor_v2", "")).strip()
    durations = _beat_duration_map(payload)
    items: list[dict] = []
    for idx, shot in enumerate(shots, start=1):
        shot_id = str(shot.get("shot_id", "")).strip()
        duration = float(durations.get(shot_id, 2.0))
        literal_scene = _literal_scene_description(shot)
        start_prompt = _start_prompt_text(brief, shot)
        end_prompt = _end_prompt_text(brief, shot)
        items.append(
            {
                "shot_id": shot_id,
                "chain_key": f"{shot_id}:{idx}",
                "timeline_index": idx,
                "anchor": master_anchor,
                "ref": master_anchor,
                "style_ref": "",
                "prompt_text": end_prompt,
                "start_prompt_text": start_prompt,
                "end_prompt_text": end_prompt,
                "style_clause": "",
                "subject_clause": str(brief.get("ref_subject_intro", "")).strip(),
                "action_clause": f"begin from {_start_action_from_shot(shot)} and end with {_end_action_from_shot(shot)} inside {literal_scene}",
                "camera_clause": str(shot.get("camera_intent", "")).strip(),
                "environment_clause": "",
                "continuity_clause": _continuity_clause(brief),
                "duration_sec": duration,
                "clip_index": idx,
                "clip_count": len(shots),
                "clip_phase": "establish" if idx == 1 else ("resolve" if idx == len(shots) else "advance"),
                "shot_type": "DETAIL_INSERT",
                "section_name": str(shot.get("section_name", "")).strip(),
                "section_label": str(shot.get("section_label", "")).strip(),
                "is_chorus": "chorus" in str(shot.get("section_label", "")).lower(),
                "camera_language": str(shot.get("camera_intent", "")).strip(),
                "pose_delta": str(shot.get("performance_intent", "")).strip(),
                "emotion": str(shot.get("transition_intent", "")).strip(),
                "scene_detail": literal_scene,
                "environment_family": str(shot.get("environment_family", "")).strip(),
                "camera_distance_band": str(shot.get("camera_distance_band", "")).strip(),
                "contact_intent": str(shot.get("contact_intent", "")).strip(),
                "motion_hint": str(shot.get("motion_intent", "")).strip(),
                "space_relation": str(shot.get("zone", "")).strip(),
                "kinetic_transition": "carry",
                "lighting_fx": str(shot.get("lighting_intent", "")).strip(),
                "kinetic_intensity": "medium",
                "route_reason": "v2_ref_pair",
                "scene_change_level": "evolve",
                "anchor_strategy": "refine_anchor",
                "continuity_basis": "heroine",
            }
        )
    return {"items": items}


def _clip_routes_from_v2(payload: dict, flux2_ref_images: list[dict]) -> list[dict]:
    shots = [row for row in payload.get("render_plan_v2", {}).get("shot_packages", []) if isinstance(row, dict)]
    durations = _beat_duration_map(payload)
    ref_map = {str(row.get("shot_id", "")).strip(): row for row in flux2_ref_images if isinstance(row, dict)}
    routes: list[dict] = []
    for idx, shot in enumerate(shots, start=1):
        shot_id = str(shot.get("shot_id", "")).strip()
        ref_row = ref_map.get(shot_id, {})
        routes.append(
            {
                "shot_id": shot_id,
                "lyric_beat_id": shot_id,
                "anchor": str(payload.get("master_anchor_v2", "")).strip(),
                "duration_sec": float(durations.get(shot_id, 2.0)),
                "use_ref": True,
                "route_reason": "v2_ref_pair",
                "mv_function": str(shot.get("story_role", "")).strip(),
                "hero_frame_score": 2,
                "consistency_need": "high",
                "section_name": str(shot.get("section_name", "")).strip(),
                "section_label": str(shot.get("section_label", "")).strip(),
                "prompt_focus": "space",
                "face_exposure_level": "soft",
                "continuity_priority": "high",
                "clip_index": idx,
                "clip_count": len(shots),
                "timeline_index": idx,
                "chain_key": f"{shot_id}:{idx}",
                "start": str(ref_row.get("start", "")),
                "end": str(ref_row.get("end", "")),
            }
        )
    return routes


def _start_prompt_text(brief: dict, shot: dict) -> str:
    return _join_sentences(
        _ref_subject_clause(brief, shot, "start"),
        _ref_state_clause(shot, "start"),
        _ref_location_clause(shot),
        _ref_continuity_clause(shot, "start"),
        _ref_camera_clause(shot, "start"),
        _ref_lighting_clause(shot),
        brief.get("ref_frame_style", ""),
    )


def _end_prompt_text(brief: dict, shot: dict) -> str:
    return _join_sentences(
        _ref_subject_clause(brief, shot, "end"),
        _ref_state_clause(shot, "end"),
        _ref_location_clause(shot),
        _ref_continuity_clause(shot, "end"),
        _ref_camera_clause(shot, "end"),
        _ref_lighting_clause(shot),
        brief.get("ref_frame_style", ""),
    )


def _start_action_from_shot(shot: dict) -> str:
    zone = str(shot.get("zone", "")).strip().lower()
    family = str(shot.get("environment_family", "")).strip().lower()
    motif = str(shot.get("motif_family", "")).strip().lower()
    visual_role = str(shot.get("visual_role", "")).strip().lower()
    if visual_role == "payoff_frame":
        if family == "stair_landing":
            return "opens into the stair landing with one step already weighted into the depth while the free side is still arriving"
        if family == "wet_curb_reflection":
            return "moves beside the wet curb with the leading step still tracing the edge while the body is still opening unevenly"
        if family == "wet_pavement_reflection":
            return "moves across the wet pavement with the broader stride still in progress and the body not yet fully settled"
        if family == "ticket_gate_lane":
            return "clears the gate line while still moving in the same lane direction instead of settling into a centered pose"
        if family == "train_window_glass":
            return "keeps moving beside the glass line while the reflected travel continues past her"
    if visual_role == "opening_frame":
        if family == "wet_curb_reflection":
            return "is caught at the first curbside step with the body already angled into the street depth"
        if family == "wet_pavement_reflection":
            return "is caught before the reflected step fully lands on the wet pavement"
        if family == "ticket_gate_lane":
            return "is caught just entering the lane while the shoulders are already turning through the gate geometry"
        if family == "stair_landing":
            return "is caught on the first stair step with the torso already angled into the stair depth"
        return "is caught at the first readable movement rather than in a settled standing pose"
    if visual_role == "handoff_frame":
        if family == "stair_landing":
            return "keeps moving into the next stair step with weight already shifted forward"
        if family == "ticket_gate_lane":
            return "keeps moving through the lane opening instead of settling into a held pose"
        if family in {"wet_curb_reflection", "wet_pavement_reflection"}:
            return "keeps moving through the reflective ground with the next step already pulling forward"
        return "keeps moving in the same direction with the action still carrying into the next cut"
    if zone in {"threshold", "edge"}:
        return "is held just before the movement fully commits"
    if zone == "compression":
        return "stays contained inside the space without settling into a presentation pose"
    if family == "train_window_glass" or "window" in motif:
        return "keeps moving beside the glass with the profile line still clear"
    if family == "ticket_gate_lane" or "gate" in motif:
        return "keeps moving just ahead of the gate line with the shoulders already set into the lane direction"
    if family == "wet_curb_reflection":
        return "keeps one step near the wet curb before the reflected movement fully opens beside her"
    if family == "wet_pavement_reflection" or "reflection" in motif or "puddle" in motif:
        return "moves above the wet pavement before the reflected step fully lands"
    return "stays inside a readable in-between moment rather than a fixed starting pose"


def _end_action_from_shot(shot: dict) -> str:
    family = str(shot.get("environment_family", "")).strip().lower()
    zone = str(shot.get("zone", "")).strip().lower()
    action = str(shot.get("performance_intent", "")).strip().rstrip(".")
    if family == "wet_pavement_reflection":
        return "lets the step settle onto the wet pavement while the reflected body line stays readable and the body keeps carrying forward"
    if family == "wet_curb_reflection":
        return "lets the step settle near the wet curb while the reflected movement still carries beside her"
    if family == "ticket_gate_lane":
        return "moves one lane-length forward beside the ticket barriers and leaves the body ready to keep traveling instead of resetting for the camera"
    if family == "train_window_glass":
        return "carries the movement a little further along the glass and leaves the profile ready to keep traveling"
    if family == "platform_signage":
        return "finishes the movement under the platform signs without collapsing into a presentation pose"
    if family == "stair_landing":
        return "lands the next step on the stair landing and keeps the body moving through the step depth instead of resolving into a balanced pose"
    if zone == "compression":
        return "keeps the movement contained and leaves the body ready for the next small shift"
    return action or "finishes one readable action without resetting into a posed still"


def _literal_scene_description(shot: dict) -> str:
    family = str(shot.get("environment_family", "")).strip().lower()
    zone = str(shot.get("zone", "")).strip().lower()
    if family == "ticket_gate_lane":
        if zone in {"open_world", "open_world_peak"}:
            return "an open station gate aisle with waist-high card readers, metallic barrier posts, overhead station lights, and concourse depth opening behind her"
        if zone in {"threshold", "edge"}:
            return "a narrow station gate entry with waist-high card readers, metallic barrier posts, and a compressed aisle just beyond the checkpoint"
        return "a narrow station gate aisle with waist-high card readers on both sides, metallic ticket barriers, overhead station lights, and concourse depth behind her"
    if family == "wet_curb_reflection":
        if zone in {"open_world", "open_world_peak"}:
            return "an open roadside lane after rain with one raised curb edge, shallow roadside water catching storefront spill light, and city traffic glow stretching behind her"
        if zone in {"threshold", "edge"}:
            return "a tight roadside edge after rain with one raised curb, shallow water along the gutter, storefront light spill, and a narrow lane turning away behind her"
        return "a narrow side street after rain with one raised curb edge, shallow roadside water catching storefront spill light, and an empty lane trailing behind her"
    if family == "wet_pavement_reflection":
        if zone in {"open_world", "open_world_peak"}:
            return "a broad wet roadway after rain with shallow puddles, painted lane markings, reflective asphalt, and distant traffic glow stretching behind her"
        if zone in {"threshold", "edge"}:
            return "a narrow wet street after rain with shallow puddles, painted road markings, reflective asphalt, and one open lane slipping away behind her"
        return "a wet city street after rain with shallow puddles, reflective asphalt, painted lane markings, and traffic glow receding behind her"
    if family == "platform_signage":
        if zone in {"open_world", "open_world_peak"}:
            return "a platform-side concourse under overhead sign boards, fluorescent station lights, side railings, and open station depth beyond her"
        return "a platform-side walkway under overhead sign boards, fluorescent station lights, side railings, and trackside depth beyond her"
    if family == "stair_landing":
        if zone in {"open_world", "open_world_peak"}:
            return "an exterior stair landing with metal railings on both sides, receding concrete steps, and open night city light spreading beyond the landing"
        return "an exterior stair landing with metal railings on both sides, receding concrete steps, and night city light beyond the landing"
    if family == "train_window_glass":
        if zone in {"threshold", "edge"}:
            return "a train-side threshold with dark carriage glass, layered interior reflections, and passing station light outside the window line"
        return "a train-side window line with dark carriage glass, layered interior reflections, and passing station light outside"
    anchor = str(shot.get("environment_anchor", "")).strip()
    return anchor or "a readable city location with clear structure and depth around her"


def _continuity_clause(brief: dict) -> str:
    return str(brief.get("ref_continuity_guidance", "")).strip()


def _ref_subject_clause(brief: dict, shot: dict, frame: str) -> str:
    family = str(shot.get("environment_family", "")).strip().lower()
    base = str(brief.get("ref_subject_intro", "")).strip() or "The same heroine"
    if frame == "start":
        if family == "ticket_gate_lane":
            return f"{base} at the start of the shot, already committed to moving through the gate space"
        if family == "stair_landing":
            return f"{base} at the start of the shot, already entering the stair depth instead of posing for camera"
        return f"{base} at the start of the shot, caught in the middle of a real movement rather than a posed still"
    if family == "ticket_gate_lane":
        return f"{base} at the end of the shot, still traveling through the gate space and ready for the next beat"
    if family == "stair_landing":
        return f"{base} at the end of the shot, still moving through the stair depth and not yet settled"
    return f"{base} at the end of the shot, finishing one readable movement without resetting into a posed frame"


def _ref_state_clause(shot: dict, frame: str) -> str:
    return _start_action_from_shot(shot) if frame == "start" else _end_action_from_shot(shot)


def _ref_location_clause(shot: dict) -> str:
    return f"The location is {_literal_scene_description(shot)}"


def _ref_continuity_clause(shot: dict, frame: str) -> str:
    parts: list[str] = []
    carry = _carryover_clause(shot)
    transition = _incoming_transition_clause(shot) if frame == "start" else ""
    anchor = _continuity_anchor_clause(shot) if frame == "end" else ""
    axis = _same_axis_clause(shot) if frame == "end" else ""
    change = _new_change_clause(shot, frame)
    for part in (carry, transition, anchor, axis, change):
        cleaned = str(part).strip()
        if cleaned:
            parts.append(cleaned)
    if not parts:
        return ""
    return " ".join(parts)


def _ref_camera_clause(shot: dict, frame: str) -> str:
    if frame == "end":
        return _end_camera_clause(shot)
    return str(shot.get("camera_intent", "")).strip()


def _ref_lighting_clause(shot: dict) -> str:
    return str(shot.get("lighting_intent", "")).strip()


def _carryover_clause(shot: dict) -> str:
    state = str(shot.get("carryover_state", "")).strip()
    if not state:
        return ""
    if state.startswith("a clean "):
        return f"Begin from {state}"
    return f"Carry forward {state}"


def _incoming_transition_clause(shot: dict) -> str:
    transition = str(shot.get("incoming_transition", "")).strip()
    if not transition:
        return ""
    return transition


def _continuity_anchor_clause(shot: dict) -> str:
    anchor = str(shot.get("continuity_anchor", "")).strip()
    return f"Keep continuity through {anchor}" if anchor else ""


def _new_change_clause(shot: dict, frame: str) -> str:
    change = str(shot.get("new_change", "")).strip()
    if not change:
        return ""
    if frame == "start":
        return f"At this start frame, introduce only {change}"
    return f"By the end frame, complete {change}"


def _end_camera_clause(shot: dict) -> str:
    family = str(shot.get("environment_family", "")).strip().lower()
    band = str(shot.get("camera_distance_band", "")).strip().lower()
    if family == "wet_pavement_reflection":
        return "Keep the camera at the same street-level medium-wide distance and continue along the wet pavement without switching to a framed window or platform view, keeping her on the same side of the frame"
    if family == "wet_curb_reflection":
        return "Keep the camera at the same curbside medium-wide distance and continue the shot beside the reflective edge without changing geography, keeping the same offset instead of recentering her"
    if family == "ticket_gate_lane":
        return "Keep the camera at the same medium-wide gate-lane distance with waist-high ticket barriers still readable beside her, preserving the same lane-side offset and body axis"
    if family == "train_window_glass":
        return "Keep the camera at the same side-on medium distance with the glass and reflections still readable beside her, without rotating into a frontal hero angle or recentering her"
    if family == "platform_signage":
        return "Keep the camera at the same medium-wide platform distance with signs and lamps still readable behind her, preserving the same offset directional feel"
    if family == "stair_landing":
        return "Keep the camera at the same medium-wide stair-landing distance with railings and receding steps still readable, preserving the same off-center side and avoiding a centered symmetrical hero frame"
    if band == "medium_wide":
        return "Keep the camera at the same medium-wide distance and continue inside the same geography"
    return str(shot.get("camera_intent", "")).strip()


def _same_axis_clause(shot: dict) -> str:
    role = str(shot.get("visual_role", "")).strip().lower()
    family = str(shot.get("environment_family", "")).strip().lower()
    if role != "payoff_frame":
        return ""
    if family == "stair_landing":
        return "Keep the same stair-side offset and body axis from the start frame, and advance only one small step further into the landing"
    if family == "wet_curb_reflection":
        return "Keep the same curbside offset and body axis from the start frame, and advance only one small state change"
    if family == "wet_pavement_reflection":
        return "Keep the same street-level offset and body axis from the start frame, and advance only one small state change"
    if family == "ticket_gate_lane":
        return "Keep the same lane-side offset and body axis from the start frame, and advance only one small state change"
    if family == "train_window_glass":
        return "Keep the same side-on body axis from the start frame, and advance only one small state change along the glass line"
    if family == "platform_signage":
        return "Keep the same platform-side offset and body axis from the start frame, and advance only one small state change"
    return "Keep the same screen-side offset and body axis from the start frame, and advance only one small state change"


def _sentence(text: str) -> str:
    cleaned = " ".join(str(text).strip().rstrip(". ").split())
    return f"{cleaned}." if cleaned else ""


def _join_sentences(*parts: object) -> str:
    return " ".join(_sentence(part) for part in parts if _sentence(part))


def _beat_duration_map(payload: dict) -> dict[str, float]:
    out: dict[str, float] = {}
    timeline = payload.get("lyrics_timeline", {})
    for section in timeline.get("sections", []):
        if not isinstance(section, dict):
            continue
        for beat in section.get("lyric_beats", []):
            if not isinstance(beat, dict):
                continue
            beat_id = str(beat.get("beat_id", "")).strip()
            if not beat_id:
                continue
            start = float(beat.get("start_sec", 0.0) or 0.0)
            end = float(beat.get("end_sec", 0.0) or 0.0)
            out[beat_id] = max(0.5, end - start) if end > start else 2.0
    return out
