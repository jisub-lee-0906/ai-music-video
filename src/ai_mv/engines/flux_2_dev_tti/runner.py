from __future__ import annotations

from ai_mv.core.output_paths import master_anchor_prefix, shot_anchor_prefix
from ai_mv.core.workflow_names import TTI_WORKFLOW
from ai_mv.infra.comfy_outputs import pick_image_file
from ai_mv.engines.flux_2_dev_tti.mapper import map_tti_workflow, tti_required_inputs
from ai_mv.infra.comfy_client import run_workflow


def run_tti(config: dict, plan: dict) -> list[dict]:
    master = plan["master_anchor"]
    out: list[dict] = []
    shots = plan["shots"]
    if not shots:
        raise RuntimeError("TTI plan is empty")
    identity_anchor = _run_master(config, master)
    for shot in shots:
        shot_anchor = _run_shot_anchor(config, shot)
        out.append(_pack_anchor(shot, identity_anchor, shot_anchor))
    return out


def _run_master(config: dict, master: dict) -> str:
    payload = dict(master)
    payload["filename_prefix"] = master_anchor_prefix()
    result = _run_shot_tti(config, payload, "character_master")
    return pick_image_file(result["files"], "TTI character_master")


def _run_shot_tti(config: dict, shot: dict, shot_id: str) -> dict:
    return run_workflow(
        config,
        TTI_WORKFLOW,
        map_tti_workflow(config, dict(shot)),
        tti_required_inputs(),
    )


def _run_shot_anchor(config: dict, shot: dict) -> str:
    payload = dict(shot)
    payload["filename_prefix"] = shot_anchor_prefix(str(shot.get("shot_id", "")))
    result = _run_shot_tti(config, payload, str(shot.get("shot_id", "")))
    return pick_image_file(result["files"], f"TTI {shot.get('shot_id', '')}")


def _pack_anchor(shot: dict, identity_anchor: str, shot_anchor: str) -> dict:
    return {
        "shot_id": shot["shot_id"],
        "anchor": shot_anchor,
        "shot_anchor": shot_anchor,
        "identity_anchor": identity_anchor,
        "shot_type": shot["shot_type"],
        "section_name": str(shot.get("section_name", "section")),
        "section_label": str(shot.get("section_label", shot.get("section_name", "section"))),
        "duration_sec": float(shot["duration_sec"]),
        "is_chorus": bool(shot["is_chorus"]),
        "lyric_beat_id": str(shot.get("lyric_beat_id", "")),
        "line_refs": list(shot.get("line_refs", [])),
        "literal_image": str(shot.get("literal_image", "")),
        "symbolic_image": str(shot.get("symbolic_image", "")),
        "motif_object": str(shot.get("motif_object", "")),
        "edit_device": str(shot.get("edit_device", "")),
        "prompt_focus": str(shot.get("prompt_focus", "")),
        "space_event": str(shot.get("space_event", "")),
        "continuity_lock": str(shot.get("continuity_lock", "")),
        "edit_role": str(shot.get("edit_role", "")),
        "camera_language": str(shot.get("camera_language", "")),
        "pose_delta": str(shot.get("pose_delta", "")),
        "emotion": str(shot.get("emotion", "")),
        "scene_detail": str(shot.get("scene_detail", "")),
        "motion_hint": str(shot.get("motion_hint", "")),
        "workflow_motion_clause": str(shot.get("workflow_motion_clause", "")),
        "space_relation": str(shot.get("space_relation", "")),
        "start_frame": dict(shot.get("start_frame", {})),
        "end_frame": dict(shot.get("end_frame", {})),
        "kinetic_transition": str(shot.get("kinetic_transition", "")),
        "lighting_fx": str(shot.get("lighting_fx", "")),
        "kinetic_intensity": str(shot.get("kinetic_intensity", "")),
        "location_family": str(shot.get("location_family", "")),
        "composition_shape": str(shot.get("composition_shape", "")),
        "palette_mode": str(shot.get("palette_mode", "")),
        "character_render_mode": str(shot.get("character_render_mode", "")),
        "face_exposure_level": str(shot.get("face_exposure_level", "partial")),
        "heroine_visibility": str(shot.get("heroine_visibility", "clear")),
        "continuity_priority": str(shot.get("continuity_priority", "low")),
        "wardrobe_read": str(shot.get("wardrobe_read", "low")),
        "hero_frame_score": int(shot.get("hero_frame_score", 1)),
        "consistency_need": str(shot.get("consistency_need", "low")),
        "mv_function": str(shot.get("mv_function", "coverage")),
        "return_weight": int(shot.get("return_weight", 1)),
        "edit_density": str(shot.get("edit_density", "medium")),
        "shot_priority": str(shot.get("shot_priority", "support")),
        "transition_role": str(shot.get("transition_role", "carry")),
        "retry": 0,
        "error_body": "",
    }
