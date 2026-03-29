from __future__ import annotations

from ai_mv.core.contracts.stage_io import StageInput, StageOutput
from ai_mv.core.stages.payload_views import merge_planner_prompt
from ai_mv.engines.seedance_v2_scene_plan.planner import build_scene_plan_v2, build_scene_plan_v2_preview_prompt


def run_scene_plan_v2(stage_input: StageInput) -> StageOutput:
    plan = build_scene_plan_v2(stage_input.config, stage_input.payload)
    return StageOutput("scene_plan_v2", "done", _build_payload(stage_input.payload, plan, stage_input.config), [])


def build_scene_plan_v2_preview_payload(config: dict, payload: dict) -> dict:
    plan = build_scene_plan_v2(config, payload)
    return _build_payload(payload, plan, config)


def _build_payload(payload: dict, plan: dict, config: dict) -> dict:
    workflow_v2 = dict(payload.get("workflow_inputs_v2", {}))
    workflow_v2["scene_plan_v2"] = {
        "brief_name": plan["brief_name"],
        "zone_progression": list(plan.get("zone_progression", [])),
        "motif_progression": list(plan.get("motif_progression", [])),
        "shot_packages": list(plan.get("shot_packages", [])),
    }
    return {
        "scene_plan_v2": plan,
        "workflow_inputs_v2": workflow_v2,
        "planner_prompts": merge_planner_prompt(
            payload,
            "scene_plan_v2",
            {"prompt": build_scene_plan_v2_preview_prompt(config, payload)},
        ),
    }
