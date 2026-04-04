from __future__ import annotations

from ai_mv.core.contracts.stage_io import StageInput, StageOutput
from ai_mv.core.director_brief import build_director_brief_intent
from ai_mv.core.prompt_grammar import wan_transition_family
from ai_mv.core.stages.payload_views import merge_planner_prompt
from ai_mv.engines.wan_2_2_flf2v.runner import run_wan
from ai_mv.utils.text_utils import parse_target


def run_wan_interpolation(stage_input: StageInput) -> StageOutput:
    plan = build_wan_plan(stage_input.config, stage_input.payload)
    clips = run_wan(stage_input.config, plan)
    workflow_inputs = dict(stage_input.payload.get("workflow_inputs", {}))
    workflow_inputs["wan_interpolation"] = {
        "clip_count": len(plan["clips"]),
        "clips": [
            {
                "shot_id": str(clip["shot_id"]),
                "start_ref_shot_id": str(clip.get("start_ref_shot_id", "")),
                "end_ref_shot_id": str(clip.get("end_ref_shot_id", "")),
                "start": str(clip.get("start", "")),
                "end": str(clip.get("end", "")),
                "positive_prompt": str(clip["positive_prompt"]),
            }
            for clip in plan["clips"]
        ],
    }
    return StageOutput(
        "wan_interpolation",
        "done",
        {
            "clips": clips,
            "workflow_inputs": workflow_inputs,
            "planner_prompts": merge_planner_prompt(
                stage_input.payload,
                "wan_interpolation",
                {"prompt": "Generate WAN prompts from adjacent REF keyframes only, using prompt_plan.wan_items."},
            ),
        },
        [],
    )


def build_wan_plan(config: dict, payload: dict) -> dict:
    brief = build_director_brief_intent(config)
    fps = parse_target(config["video"]["target"])[2]
    ref_map = {str(row.get("shot_id", "")).strip(): row for row in payload.get("flux2_ref_images", []) if isinstance(row, dict)}
    chains = [row for row in payload.get("prompt_plan", {}).get("wan_items", []) if isinstance(row, dict)]
    clips: list[dict] = []
    for index, chain in enumerate(chains, start=1):
        start_ref_shot_id = str(chain.get("start_ref_shot_id", "")).strip()
        end_ref_shot_id = str(chain.get("end_ref_shot_id", "")).strip()
        start_ref = ref_map[start_ref_shot_id]
        end_ref = ref_map[end_ref_shot_id]
        transition_family = str(chain.get("wan_transition_family", "")).strip()
        transition = wan_transition_family(transition_family)
        duration_sec = float(chain.get("duration_sec", 2.0) or 2.0)
        clips.append(
            {
                "shot_id": str(chain.get("shot_id", "")).strip(),
                "start": str(start_ref["end"]),
                "end": str(end_ref["end"]),
                "start_ref_index": int(start_ref.get("timeline_index", 0) or 0),
                "end_ref_index": int(end_ref.get("timeline_index", 0) or 0),
                "fps": fps,
                "frames": max(_frame_floor(fps), int(round(duration_sec * fps))),
                "section_name": str(chain.get("section_name", "")).strip(),
                "section_label": str(chain.get("section_label", "")).strip(),
                "shot_type": "DETAIL_INSERT",
                "is_chorus": "chorus" in str(chain.get("section_label", "")).lower(),
                "pose_delta": "",
                "emotion": "",
                "scene_detail": str(chain.get("why", "")).strip(),
                "space_relation": str(chain.get("section_label", "")).strip(),
                "start_frame": {},
                "end_frame": {},
                "kinetic_transition": "carry",
                "lighting_fx": "",
                "kinetic_intensity": "high" if "chorus" in str(chain.get("section_label", "")).lower() else "medium",
                "location_family": "",
                "symbolic_image": "",
                "motif_object": "",
                "edit_device": "",
                "prompt_focus": "space",
                "space_event": str(chain.get("why", "")).strip(),
                "palette_mode": "",
                "character_render_mode": "",
                "face_exposure_level": "soft",
                "heroine_visibility": "clear",
                "continuity_priority": "high",
                "wardrobe_read": "high",
                "continuity_lock": "",
                "route_reason": "adjacent_ref_pair",
                "scene_change_level": "evolve",
                "anchor_strategy": "refine_anchor",
                "use_ref": True,
                "clip_index": index,
                "clip_count": len(chains),
                "timeline_index": index,
                "chain_key": f"{start_ref_shot_id}->{end_ref_shot_id}",
                "start_source": "previous_ref_end",
                "prev_chain_key": "",
                "start_ref_shot_id": start_ref_shot_id,
                "end_ref_shot_id": end_ref_shot_id,
                "duration_sec": duration_sec,
                "lighting_intent": "",
                "location_description": str(chain.get("wan_prompt_atoms", {}).get("primary_surface", "")).strip(),
                "literal_image": "",
                "visible_action": str(chain.get("wan_prompt_atoms", {}).get("bridge_action", "")).strip(),
                "subject_action": str(chain.get("wan_prompt_atoms", {}).get("bridge_action", "")).strip(),
                "wan_action_line": str(chain.get("wan_prompt_atoms", {}).get("bridge_action", "")).strip(),
                "wan_transition_family": transition_family,
                "wan_transition_contract": str(transition.get("contract", "")).strip(),
                "positive_prompt": str(chain.get("wan_positive_prompt_text", "")).strip() or _wan_positive_prompt(brief, chain),
                "negative_prompt": _wan_negative_prompt(brief),
                "energy": "high" if "chorus" in str(chain.get("section_label", "")).lower() else "normal",
            }
        )
    return {"clips": clips}


def _wan_positive_prompt(brief: dict, chain: dict) -> str:
    atoms = dict(chain.get("wan_prompt_atoms", {}))
    parts = [
        str(atoms.get("subject_intro", "")).strip(),
        str(atoms.get("location", "")).strip(),
        str(atoms.get("bridge_action", "")).strip(),
    ]
    return " ".join(f"{part.rstrip('.')}." for part in parts if part)


def _wan_negative_prompt(brief: dict) -> str:
    return str(brief.get("wan_negative", "")).strip()


def _frame_floor(fps: int) -> int:
    return max(1, int(round(max(1, fps) * 0.25)))
