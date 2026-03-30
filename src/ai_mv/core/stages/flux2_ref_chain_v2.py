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
                "action_clause": f"begin from {_start_action_from_shot(shot)} and end with {_end_action_from_shot(shot)} inside {shot['environment_anchor']}",
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
                "scene_detail": str(shot.get("environment_anchor", "")).strip(),
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


def _action_from_shot(shot: dict) -> str:
    return _end_action_from_shot(shot)


def _start_prompt_text(brief: dict, shot: dict) -> str:
    return (
        f"{brief['ref_subject_intro']} at the start of the shot, {_start_action_from_shot(shot)} inside {shot['environment_anchor']}. "
        f"{_sentence(_visual_role_clause(shot, 'start'))} "
        f"{_sentence(_carryover_clause(shot))} "
        f"{_sentence(_continuity_anchor_clause(shot))} "
        f"{_sentence(_new_change_clause(shot, 'start'))} "
        f"{_sentence(_physical_space_clause(shot))} "
        f"{_sentence(_camera_band_clause(shot))} "
        f"{_sentence(_contact_clause(shot))} "
        f"{_sentence(shot['camera_intent'])} "
        f"{_sentence(shot.get('lighting_intent', ''))} "
        f"{_sentence(shot.get('shadow_intent', ''))} "
        f"{_sentence(brief.get('ref_frame_style', ''))}"
    )


def _end_prompt_text(brief: dict, shot: dict) -> str:
    return (
        f"{brief['ref_subject_intro']} at the end of the shot, {_end_action_from_shot(shot)} inside {shot['environment_anchor']}. "
        f"{_sentence(_visual_role_clause(shot, 'end'))} "
        f"{_sentence(_carryover_clause(shot))} "
        f"{_sentence(_continuity_anchor_clause(shot))} "
        f"{_sentence(_new_change_clause(shot, 'end'))} "
        f"{_sentence(_physical_space_clause(shot))} "
        f"{_sentence(_camera_band_clause(shot))} "
        f"{_sentence(_contact_clause(shot))} "
        f"{_sentence(_end_camera_clause(shot))} "
        f"{_sentence(shot.get('lighting_intent', ''))} "
        f"{_sentence(shot.get('shadow_intent', ''))} "
        f"{_sentence(brief.get('ref_frame_style', ''))}"
    )


def _start_action_from_shot(shot: dict) -> str:
    zone = str(shot.get("zone", "")).strip().lower()
    family = str(shot.get("environment_family", "")).strip().lower()
    motif = str(shot.get("motif_family", "")).strip().lower()
    visual_role = str(shot.get("visual_role", "")).strip().lower()
    if visual_role == "payoff_frame":
        if family == "stair_landing":
            return "opens into the payoff on the stair landing with one step weighted into the depth and a hand or shoulder still tied to the rail"
        if family == "wet_curb_reflection":
            return "opens into the payoff with the leading step still tracing the wet curb and the body opening into the street depth"
        if family == "wet_pavement_reflection":
            return "opens into the payoff with a broader stride while the reflected step still reads in the wet pavement"
        if family == "ticket_gate_lane":
            return "opens into the payoff through the gate lane while one shoulder still acknowledges the barrier line"
        if family == "train_window_glass":
            return "opens into the payoff while keeping the body still tied to the glass line and reflected travel"
    if visual_role == "opening_frame":
        if family == "wet_curb_reflection":
            return "catches the first moment of a curbside step with the body already angled into the street depth"
        if family == "wet_pavement_reflection":
            return "catches the first readable movement above the wet pavement before the reflected step fully lands"
        if family == "ticket_gate_lane":
            return "catches the first lane-entry moment with the shoulders already turning through the gate geometry"
        if family == "stair_landing":
            return "catches the first step beside the rail with the torso already angled into the stair depth"
        return "catches the first readable movement rather than a fully settled standing pose"
    if visual_role == "handoff_frame":
        if family == "stair_landing":
            return "leans into the next stair step with weight already shifted forward and one hand ready at the rail"
        if family == "ticket_gate_lane":
            return "holds a directional stance already carrying into the next lane opening"
        if family in {"wet_curb_reflection", "wet_pavement_reflection"}:
            return "holds a directional stance with the next step already pulling forward through the reflective ground"
        return "holds a directional stance with motion already carrying into the next cut"
    if zone in {"threshold", "edge"}:
        return "holds a poised starting stance before the movement commits"
    if zone == "compression":
        return "keeps the body contained and the pose tightly controlled"
    if family == "train_window_glass" or "window" in motif:
        return "holds near the glass with the profile and hand line clearly readable"
    if family == "ticket_gate_lane" or "gate" in motif:
        return "stands just before the gate line with the shoulders still"
    if family == "wet_curb_reflection":
        return "sets one step near the wet curb before the reflected movement opens beside her"
    if family == "wet_pavement_reflection" or "reflection" in motif or "puddle" in motif:
        return "sets the body above the wet pavement before the reflected step lands"
    return "holds a clear readable starting pose"


def _end_action_from_shot(shot: dict) -> str:
    family = str(shot.get("environment_family", "")).strip().lower()
    zone = str(shot.get("zone", "")).strip().lower()
    action = str(shot.get("performance_intent", "")).strip().rstrip(".")
    if family == "wet_pavement_reflection":
        return "finishes the step on the wet pavement and holds the reflected body line clearly"
    if family == "wet_curb_reflection":
        return "completes the step near the wet curb and lets the reflected movement settle beside her"
    if family == "ticket_gate_lane":
        return "moves one lane-length forward beside the ticket barriers and settles into a readable side turn"
    if family == "train_window_glass":
        return "carries the movement a little further along the glass and settles into a readable profile"
    if family == "platform_signage":
        return "finishes the movement under the platform signs and holds a readable body turn"
    if family == "stair_landing":
        return "lands the next step on the stair landing and settles into a readable turn beside the rail"
    if zone == "compression":
        return "keeps the movement contained and settles into the next readable pose"
    return action or "shifts into the next readable pose"


def _continuity_clause(brief: dict) -> str:
    return str(brief.get("ref_continuity_guidance", "")).strip()


def _physical_space_clause(shot: dict) -> str:
    family = str(shot.get("environment_family", "")).strip().lower()
    if family == "train_window_glass":
        return "Keep the shot inside the train-window glass environment with interior reflections and passing exterior light"
    if family == "ticket_gate_lane":
        return "Keep the shot inside the ticket-gate lane with waist-high ticket barriers, card readers, and entry lane posts clearly readable"
    if family == "wet_curb_reflection":
        return "Keep the shot at street level beside the wet curb with reflective asphalt and street depth behind her"
    if family == "wet_pavement_reflection":
        return "Keep the shot at street level on wet pavement with shallow puddle reflections and open city depth around her"
    if family == "platform_signage":
        return "Keep the shot on the platform with signage, lamps, and station depth readable behind her"
    if family == "stair_landing":
        return "Keep the shot on the stair landing with railings and receding steps readable behind her"
    return "Keep the shot inside one consistent physical environment family"


def _camera_band_clause(shot: dict) -> str:
    band = str(shot.get("camera_distance_band", "")).strip().lower()
    if band == "tight_medium":
        return "Keep both keyframes inside a tight-medium framing band without opening into a wide shot"
    if band == "medium_wide":
        return "Keep both keyframes inside a medium-wide framing band and do not jump to an extreme close-up or distant wide shot"
    if band == "wide_full_figure":
        return "Keep both keyframes inside a wide full-figure framing band with the heroine fully readable in the environment"
    return "Keep both keyframes inside one stable framing band"


def _contact_clause(shot: dict) -> str:
    return str(shot.get("contact_intent", "")).strip()


def _carryover_clause(shot: dict) -> str:
    state = str(shot.get("carryover_state", "")).strip()
    if not state:
        return ""
    if state.startswith("a clean "):
        return f"Begin from {state}"
    return f"Carry forward {state}"


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


def _visual_role_clause(shot: dict, frame: str) -> str:
    role = str(shot.get("visual_role", "")).strip().lower()
    if role == "opening_frame":
        if frame == "start":
            return "Make this feel like the first cinematic image of the beat rather than a centered catalog pose"
        return "Let the ending frame stay cinematic and spatially tense instead of flattening into a promotional still"
    if role == "handoff_frame":
        return "Make the frame feel ready to hand motion and screen direction into the next cut"
    if role == "pressure_frame":
        return "Keep the frame pressurized and focused, with less pose presentation and more immediate scene tension"
    if role == "payoff_frame":
        return "Let the frame feel like a cinematic release with broader world presence, not just a clean fashion still"
    return "Keep the frame inside a connected cinematic moment rather than a standalone posed still"


def _end_camera_clause(shot: dict) -> str:
    family = str(shot.get("environment_family", "")).strip().lower()
    band = str(shot.get("camera_distance_band", "")).strip().lower()
    if family == "wet_pavement_reflection":
        return "Keep the camera at the same street-level medium-wide distance and continue along the wet pavement without switching to a framed window or platform view"
    if family == "wet_curb_reflection":
        return "Keep the camera at the same curbside medium-wide distance and continue the shot beside the reflective edge without changing geography"
    if family == "ticket_gate_lane":
        return "Keep the camera at the same medium-wide gate-lane distance with waist-high ticket barriers still readable beside her"
    if family == "train_window_glass":
        return "Keep the camera at the same side-on medium distance with the glass and reflections still readable beside her"
    if family == "platform_signage":
        return "Keep the camera at the same medium-wide platform distance with signs and lamps still readable behind her"
    if family == "stair_landing":
        return "Keep the camera at the same medium-wide stair-landing distance with railings and receding steps still readable"
    if band == "medium_wide":
        return "Keep the camera at the same medium-wide distance and continue inside the same geography"
    return str(shot.get("camera_intent", "")).strip()


def _sentence(text: str) -> str:
    cleaned = " ".join(str(text).strip().rstrip(". ").split())
    return f"{cleaned}." if cleaned else ""


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
