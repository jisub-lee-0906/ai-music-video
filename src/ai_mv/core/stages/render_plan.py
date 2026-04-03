from __future__ import annotations

from ai_mv.core.contracts.stage_io import StageInput, StageOutput
from ai_mv.core.stages.payload_views import merge_planner_prompt
from ai_mv.engines.render_plan.planner import build_prompt_plan, build_prompt_plan_preview_prompt


def run_render_plan(stage_input: StageInput) -> StageOutput:
    plan = build_prompt_plan(stage_input.config, stage_input.payload)
    return StageOutput("prompt_plan", "done", _build_payload(stage_input.payload, plan, stage_input.config), [])


def build_render_plan_preview_payload(config: dict, payload: dict) -> dict:
    plan = build_prompt_plan(config, payload)
    return _build_payload(payload, plan, config)


def _build_payload(payload: dict, plan: dict, config: dict) -> dict:
    workflow_inputs = dict(payload.get("workflow_inputs", {}))
    workflow_inputs["prompt_plan"] = {
        "master_anchor": dict(plan.get("master_anchor", {})),
        "ref_items": list(plan.get("ref_items", [])),
        "wan_items": list(plan.get("wan_items", [])),
    }
    return {
        "prompt_plan": plan,
        "workflow_inputs": workflow_inputs,
        "planner_prompts": merge_planner_prompt(
            payload,
            "prompt_plan",
            {"prompt": build_prompt_plan_preview_prompt(config, payload)},
        ),
    }
