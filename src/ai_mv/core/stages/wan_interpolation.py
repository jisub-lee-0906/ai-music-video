from __future__ import annotations

from ai_mv.core.contracts.stage_io import StageInput, StageOutput
from ai_mv.core.director_brief import build_director_brief_intent
from ai_mv.core.prompt_grammar import wan_transition_family
from ai_mv.core.stages.flux2_ref_chain import _literal_scene_description
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
                "start_source": str(clip.get("start_source", "")),
                "prev_chain_key": str(clip.get("prev_chain_key", "")),
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
                {"prompt": "Generate WAN start/end clip prompts from adjacent REF keyframes using end-to-end chaining (1-2, 2-3, 3-4)."},
            ),
        },
        [],
    )


def build_wan_plan(config: dict, payload: dict) -> dict:
    brief = build_director_brief_intent(config)
    fps = parse_target(config["video"]["target"])[2]
    ref_map = {str(row.get("shot_id", "")).strip(): row for row in payload.get("flux2_ref_images", []) if isinstance(row, dict)}
    chains = [row for row in payload.get("render_plan", {}).get("wan_chain", []) if isinstance(row, dict)]
    clips: list[dict] = []
    for index, chain in enumerate(chains, start=1):
        shot_id = str(chain.get("shot_id", "")).strip()
        start_ref_shot_id = str(chain.get("start_ref_shot_id", "")).strip() or shot_id
        end_ref_shot_id = str(chain.get("end_ref_shot_id", "")).strip() or shot_id
        start_ref = ref_map[start_ref_shot_id]
        end_ref = ref_map[end_ref_shot_id]
        start = str(start_ref["end"])
        end = str(end_ref["end"])
        duration_sec = float(chain.get("duration_sec", 2.0))
        chain["duration_sec"] = duration_sec
        frames = max(_frame_floor(fps), int(round(duration_sec * fps)))
        positive = _wan_positive_prompt(brief, chain)
        negative = _wan_negative_prompt(brief)
        transition_family = str(chain.get("wan_transition_family", "")).strip()
        transition = wan_transition_family(transition_family)
        clips.append(
            {
                "shot_id": shot_id,
                "start": start,
                "end": end,
                "fps": fps,
                "frames": frames,
                "section_name": str(chain.get("section_name", "")).strip(),
                "section_label": str(chain.get("section_label", "")).strip(),
                "shot_type": "DETAIL_INSERT",
                "is_chorus": "chorus" in str(chain.get("section_label", "")).lower(),
                "pose_delta": "",
                "emotion": "",
                "scene_detail": str(chain.get("environment_anchor", "")).strip(),
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
                "space_event": str(chain.get("environment_anchor", "")).strip(),
                "palette_mode": "",
                "character_render_mode": "",
                "face_exposure_level": str(chain.get("face_exposure_level", "")).strip(),
                "heroine_visibility": "clear",
                "continuity_priority": str(chain.get("continuity_priority", "")).strip(),
                "wardrobe_read": "high",
                "continuity_lock": "",
                "route_reason": str(chain.get("route_reason", "")).strip(),
                "scene_change_level": "evolve",
                "anchor_strategy": "refine_anchor",
                "use_ref": True,
                "clip_index": int(chain.get("clip_index", index)),
                "clip_count": int(chain.get("clip_count", len(chains))),
                "timeline_index": int(chain.get("timeline_index", index)),
                "chain_key": str(chain.get("chain_key", f"{shot_id}:{index}")).strip(),
                "start_source": str(chain.get("start_source", "previous_ref_end")).strip(),
                "prev_chain_key": str(chain.get("previous_chain_key", "")).strip(),
                "start_ref_shot_id": start_ref_shot_id,
                "end_ref_shot_id": end_ref_shot_id,
                "duration_sec": duration_sec,
                "lighting_intent": str(chain.get("lighting_intent", "")).strip(),
                "location_description": str(chain.get("location_description", "")).strip(),
                "literal_image": str(chain.get("literal_image", "")).strip(),
                "visible_action": str(chain.get("visible_action", "")).strip(),
                "subject_action": str(chain.get("subject_action", "")).strip(),
                "wan_action_line": str(chain.get("wan_action_line", "")).strip(),
                "wan_transition_family": transition_family,
                "wan_transition_contract": str(transition.get("contract", "")).strip(),
                "positive_prompt": positive,
                "negative_prompt": negative,
                "energy": _energy_for_section(str(chain.get('section_label', '')).strip()),
            }
        )
    return {"clips": clips}
def _wan_positive_prompt(brief: dict, chain: dict) -> str:
    verbalized = str(chain.get("wan_positive_prompt_text", "")).strip()
    if verbalized:
        return verbalized
    location = _literal_scene_description(chain).rstrip(".")
    subject = str(brief.get("ref_subject_intro", "")).strip().rstrip(".") or "The same Korean female idol"
    parts = [
        f"In {location}" if location else "",
        subject,
        _wan_action_sentence(chain),
        _wan_lighting_sentence(chain),
    ]
    return " ".join(_sentence(part) for part in parts if _sentence(part))


def _wan_negative_prompt(brief: dict) -> str:
    return str(brief.get("wan_negative", "")).strip()


def _energy_for_section(section_label: str) -> str:
    low = section_label.lower()
    if "final chorus" in low or "chorus" in low:
        return "high"
    if "bridge" in low:
        return "normal"
    return "low"


def _frame_floor(fps: int) -> int:
    return max(1, int(round(max(1, fps) * 0.25)))


def _wan_action_sentence(chain: dict) -> str:
    natural = str(chain.get("wan_action_line", "")).strip()
    if natural:
        return natural
    subject_action = str(chain.get("subject_action", "")).strip()
    if subject_action:
        return subject_action
    visible_action = str(chain.get("visible_action", "")).strip()
    if visible_action:
        return visible_action
    return str(chain.get("performance_intent", "")).strip()


def _wan_lighting_sentence(chain: dict) -> str:
    return str(chain.get("lighting_intent", "")).strip()


def _sentence(text: str) -> str:
    cleaned = " ".join(str(text).strip().rstrip(". ").split())
    return f"{cleaned}." if cleaned else ""
