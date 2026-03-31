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
                "action_clause": "",
                "camera_clause": str(shot.get("camera_intent", "")).strip(),
                "environment_clause": "",
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
    verbalized = str(shot.get("ref_start_prompt_text", "")).strip()
    if verbalized:
        return verbalized
    return _join_sentences(
        _ref_subject_clause(brief, shot, "start"),
        _ref_location_clause(shot),
        _ref_state_clause(shot, "start"),
        _ref_lighting_clause(shot),
    )


def _end_prompt_text(brief: dict, shot: dict) -> str:
    verbalized = str(shot.get("ref_end_prompt_text", "")).strip()
    if verbalized:
        return verbalized
    return _join_sentences(
        _ref_subject_clause(brief, shot, "end"),
        _ref_location_clause(shot),
        _ref_state_clause(shot, "end"),
        _ref_lighting_clause(shot),
    )


def _literal_scene_description(shot: dict) -> str:
    location = " ".join(str(shot.get("location_description", "")).strip().rstrip(".").split())
    if location:
        return location
    anchor = str(shot.get("environment_anchor", "")).strip()
    if anchor:
        return " ".join(anchor.rstrip(".").split())
    literal = " ".join(str(shot.get("literal_image", "")).strip().rstrip(".").split())
    if literal and _looks_english(literal):
        return f"a readable station-side place at night with {literal}"
    base = "a readable station-side place at night with clear physical depth around her"
    return _literal_scene_with_beat_detail(base, shot)


def _literal_scene_with_beat_detail(base: str, shot: dict) -> str:
    detail = " ".join(str(shot.get("literal_image", "")).strip().rstrip(".").split())
    base_clean = " ".join(str(base).strip().rstrip(".").split())
    if not detail or not _looks_english(detail) or detail.lower() in base_clean.lower():
        return base_clean
    return f"{base_clean}, with {detail}"


def _ref_subject_clause(brief: dict, shot: dict, frame: str) -> str:
    base = str(brief.get("ref_subject_intro", "")).strip() or "The same heroine"
    return base


def _ref_state_clause(shot: dict, frame: str) -> str:
    line_key = "ref_start_action_line" if frame == "start" else "ref_end_action_line"
    natural = str(shot.get(line_key, "")).strip()
    if natural:
        return natural
    subject_action = str(shot.get("subject_action", "")).strip()
    if subject_action:
        return subject_action
    visible_action = str(shot.get("visible_action", "")).strip()
    if visible_action:
        return visible_action
    return ""


def _ref_location_clause(shot: dict) -> str:
    location = _literal_scene_description(shot)
    return f"In {location}" if location else ""


def _ref_lighting_clause(shot: dict) -> str:
    natural = str(shot.get("ref_lighting_line", "")).strip()
    if natural:
        return natural
    return str(shot.get("lighting_intent", "")).strip()


def _looks_english(text: str) -> bool:
    letters = [ch for ch in str(text) if ch.isalpha()]
    if not letters:
        return False
    ascii_letters = [ch for ch in letters if ("a" <= ch.lower() <= "z")]
    return (len(ascii_letters) / len(letters)) >= 0.8


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
