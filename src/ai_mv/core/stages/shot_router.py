from __future__ import annotations

from ai_mv.core.contracts.stage_io import StageInput, StageOutput
from ai_mv.core.visual_pipeline import build_clip_routes, route_summary, visual_pipeline_settings


def run_shot_router(stage_input: StageInput) -> StageOutput:
    routes = build_shot_routes(stage_input.config, stage_input.payload)
    return StageOutput(
        "shot_router",
        "done",
        {
            "clip_routes": routes,
            "render_inputs": dict(stage_input.payload.get("render_inputs", {}), clip_routes=routes),
            "planner_prompts": _merge_prompt_preview(
                stage_input.payload,
                "shot_router",
                {"prompt": _route_policy_summary(stage_input.config)},
            ),
            "workflow_inputs_preview": _merge_workflow_preview(
                stage_input.payload,
                "shot_router",
                {"decisions": _route_preview(routes)},
            ),
        },
        [],
    )


def build_shot_routes(config: dict, payload: dict) -> list[dict]:
    anchors = payload.get("anchors", [])
    if not anchors:
        raise RuntimeError("anchors missing for shot_router")
    return build_clip_routes(config, anchors)


def _route_policy_summary(config: dict) -> str:
    settings = visual_pipeline_settings(config)
    return (
        f"mode={settings['visual_pipeline_mode']}; "
        f"consistency={settings['consistency_mode']}; "
        f"hero_types={','.join(settings['hero_shot_types'])}; "
        f"priority_sections={','.join(settings['reference_priority_sections'])}"
    )


def _route_preview(routes: list[dict]) -> list[dict]:
    return route_summary(routes)


def _merge_prompt_preview(payload: dict, key: str, value: dict) -> dict:
    out = dict(payload.get("planner_prompts", {}))
    out[key] = value
    return out


def _merge_workflow_preview(payload: dict, key: str, value: dict) -> dict:
    out = dict(payload.get("workflow_inputs_preview", {}))
    out[key] = value
    return out
