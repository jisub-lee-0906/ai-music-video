from __future__ import annotations

from ai_mv.core.contracts.stage_io import StageInput, StageOutput
from ai_mv.core.director_brief import build_director_brief_intent
from ai_mv.core.stages.payload_views import merge_planner_prompt
from ai_mv.engines.wan_2_2_flf2v.runner import run_wan
from ai_mv.utils.text_utils import parse_target


def run_wan_interpolation_v2(stage_input: StageInput) -> StageOutput:
    plan = build_wan_plan_v2(stage_input.config, stage_input.payload)
    clips = run_wan(stage_input.config, plan)
    workflow_v2 = dict(stage_input.payload.get("workflow_inputs_v2", {}))
    workflow_v2["wan_interpolation_v2"] = {
        "clip_count": len(plan["clips"]),
        "clips": [
            {
                "shot_id": str(clip["shot_id"]),
                "start_source": str(clip.get("start_source", "")),
                "prev_chain_key": str(clip.get("prev_chain_key", "")),
                "positive_prompt": str(clip["positive_prompt"]),
            }
            for clip in plan["clips"]
        ],
    }
    return StageOutput(
        "wan_interpolation_v2",
        "done",
        {
            "clips": clips,
            "workflow_inputs_v2": workflow_v2,
            "planner_prompts": merge_planner_prompt(
                stage_input.payload,
                "wan_interpolation_v2",
                {"prompt": "Generate WAN start/end clip prompts from the v2 render chain using previous_end continuity after the first shot."},
            ),
        },
        [],
    )


def build_wan_plan_v2(config: dict, payload: dict) -> dict:
    brief = build_director_brief_intent(config)
    fps = parse_target(config["video"]["target"])[2]
    routes = [row for row in payload.get("clip_routes", []) if isinstance(row, dict)]
    ref_map = {str(row.get("shot_id", "")).strip(): row for row in payload.get("flux2_ref_images", []) if isinstance(row, dict)}
    clip_map = {
        str(row.get("shot_id", "")).strip(): row
        for row in payload.get("render_plan_v2", {}).get("wan_chain", [])
        if isinstance(row, dict)
    }
    clips: list[dict] = []
    prev_end = ""
    prev_key = ""
    for index, route in enumerate(routes, start=1):
        shot_id = str(route.get("shot_id", "")).strip()
        ref_row = ref_map[shot_id]
        chain = clip_map[shot_id]
        start = str(ref_row["start"])
        if index > 1 and prev_end:
            start = prev_end
        end = str(ref_row["end"])
        duration_sec = float(route.get("duration_sec", 2.0))
        frames = max(_frame_floor(fps), int(round(duration_sec * fps)))
        positive = (
            f"Camera {str(chain.get('camera_intent', '')).strip().rstrip('.')} in {str(brief.get('wan_motion_style', '')).strip().rstrip('.')}. "
            f"{_wan_carryover_clause(chain)} "
            f"{_wan_anchor_clause(chain)} "
            f"{_wan_change_clause(chain)} "
            f"She {_subject_motion(chain)}. "
            f"Background {str(chain.get('environment_anchor', '')).strip().rstrip('.')}"
        )
        clips.append(
            {
                "shot_id": shot_id,
                "start": start,
                "end": end,
                "fps": fps,
                "frames": frames,
                "section_name": str(route.get("section_name", "")).strip(),
                "section_label": str(route.get("section_label", "")).strip(),
                "shot_type": "DETAIL_INSERT",
                "is_chorus": "chorus" in str(route.get("section_label", "")).lower(),
                "camera_language": str(chain.get("camera_intent", "")).strip(),
                "pose_delta": "",
                "emotion": "",
                "scene_detail": str(chain.get("environment_anchor", "")).strip(),
                "motion_hint": str(chain.get("motion_intent", "")).strip(),
                "workflow_motion_clause": str(chain.get("motion_intent", "")).strip(),
                "space_relation": str(route.get("section_label", "")).strip(),
                "start_frame": {},
                "end_frame": {},
                "kinetic_transition": "carry",
                "lighting_fx": "",
                "kinetic_intensity": "high" if "chorus" in str(route.get("section_label", "")).lower() else "medium",
                "location_family": "",
                "symbolic_image": "",
                "motif_object": "",
                "edit_device": "",
                "prompt_focus": "space",
                "space_event": str(chain.get("environment_anchor", "")).strip(),
                "composition_shape": str(chain.get("camera_intent", "")).strip(),
                "palette_mode": "",
                "character_render_mode": "",
                "face_exposure_level": str(route.get("face_exposure_level", "")).strip(),
                "heroine_visibility": "clear",
                "continuity_priority": str(route.get("continuity_priority", "")).strip(),
                "wardrobe_read": "high",
                "continuity_lock": "",
                "route_reason": str(route.get("route_reason", "")).strip(),
                "scene_change_level": "evolve",
                "anchor_strategy": "refine_anchor",
                "use_ref": True,
                "clip_index": int(route.get("clip_index", index)),
                "clip_count": int(route.get("clip_count", len(routes))),
                "timeline_index": int(route.get("timeline_index", index)),
                "chain_key": str(chain.get("chain_key", f"{shot_id}:{index}")).strip(),
                "start_source": "ref_start" if index == 1 else "previous_end",
                "prev_chain_key": "" if index == 1 else prev_key,
                "subject_motion": _subject_motion(chain),
                "camera_relation": f"Camera {str(chain.get('camera_intent', '')).strip().rstrip('.')} in {str(brief.get('wan_motion_style', '')).strip().rstrip('.')}",
                "environment_detail": f"Background {str(chain.get('environment_anchor', '')).strip().rstrip('.')}",
                "carryover_state": str(chain.get("carryover_state", "")).strip(),
                "continuity_anchor": str(chain.get("continuity_anchor", "")).strip(),
                "new_change": str(chain.get("new_change", "")).strip(),
                "positive_prompt": positive,
                "negative_prompt": str(brief.get("wan_negative", "")).strip(),
                "energy": _energy_for_section(str(route.get('section_label', '')).strip()),
            }
        )
        prev_end = end
        prev_key = str(chain.get("chain_key", f"{shot_id}:{index}")).strip()
    return {"clips": clips}


def _subject_motion(chain: dict) -> str:
    action = str(chain.get("performance_intent", "")).strip()
    if action:
        lowered = action[:1].lower() + action[1:] if action else action
        return lowered.rstrip(".")
    return "holds one readable action while the space reacts around her"


def _energy_for_section(section_label: str) -> str:
    low = section_label.lower()
    if "final chorus" in low or "chorus" in low:
        return "high"
    if "bridge" in low:
        return "normal"
    return "low"


def _frame_floor(fps: int) -> int:
    return max(1, int(round(max(1, fps) * 0.25)))


def _wan_carryover_clause(chain: dict) -> str:
    state = str(chain.get("carryover_state", "")).strip().rstrip(".")
    if not state:
        return ""
    if state.startswith("a clean "):
        return f"Begin from {state}."
    return f"Carry forward {state}."


def _wan_anchor_clause(chain: dict) -> str:
    anchor = str(chain.get("continuity_anchor", "")).strip().rstrip(".")
    return f"Keep continuity through {anchor}." if anchor else ""


def _wan_change_clause(chain: dict) -> str:
    change = str(chain.get("new_change", "")).strip().rstrip(".")
    return f"Introduce {change}." if change else ""
