from __future__ import annotations

from ai_mv.core.contracts.stage_io import StageInput, StageOutput
from ai_mv.core.stages.payload_views import merge_planner_prompt
from ai_mv.engines.scene_plan.planner import build_scene_outline, build_scene_outline_preview_prompt


def run_scene_plan(stage_input: StageInput) -> StageOutput:
    plan = build_scene_outline(stage_input.config, stage_input.payload)
    return StageOutput("scene_outline", "done", _build_payload(stage_input.payload, plan, stage_input.config), [])


def build_scene_plan_preview_payload(config: dict, payload: dict) -> dict:
    plan = build_scene_outline(config, payload)
    return _build_payload(payload, plan, config)


def _build_payload(payload: dict, plan: dict, config: dict) -> dict:
    workflow_inputs = dict(payload.get("workflow_inputs", {}))
    workflow_inputs["scene_outline"] = {
        "story_premise": plan["story_premise"],
        "shot_packages": list(plan.get("shot_packages", [])),
    }
    return {
        "scene_outline": plan,
        "workflow_inputs": workflow_inputs,
        "planner_prompts": merge_planner_prompt(
            payload,
            "scene_outline",
            {"prompt": build_scene_outline_preview_prompt(config, payload)},
        ),
    }
