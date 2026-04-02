from __future__ import annotations

from ai_mv.core.contracts.stage_io import StageInput, StageOutput
from ai_mv.core.stages.payload_views import merge_planner_prompt
from ai_mv.engines.render_plan.planner import build_render_plan, build_render_plan_preview_prompt


def run_render_plan(stage_input: StageInput) -> StageOutput:
    plan = build_render_plan(stage_input.config, stage_input.payload)
    return StageOutput("render_plan", "done", _build_payload(stage_input.payload, plan, stage_input.config), [])


def build_render_plan_preview_payload(config: dict, payload: dict) -> dict:
    plan = build_render_plan(config, payload)
    return _build_payload(payload, plan, config)


def _build_payload(payload: dict, plan: dict, config: dict) -> dict:
    workflow_inputs = dict(payload.get("workflow_inputs", {}))
    workflow_inputs["render_plan"] = {
        "master_anchor": dict(plan.get("master_anchor", {})),
        "shot_packages": list(plan.get("shot_packages", [])),
        "wan_chain": list(plan.get("wan_chain", [])),
    }
    return {
        "render_plan": plan,
        "workflow_inputs": workflow_inputs,
        "planner_prompts": merge_planner_prompt(
            payload,
            "render_plan",
            {"prompt": build_render_plan_preview_prompt(config, payload)},
        ),
    }
