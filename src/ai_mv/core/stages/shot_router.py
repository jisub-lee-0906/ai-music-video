from __future__ import annotations

from ai_mv.core.contracts.stage_io import StageInput, StageOutput
from ai_mv.core.stages.payload_views import build_stage_payload
from ai_mv.core.visual_pipeline import build_clip_routes, route_summary, visual_pipeline_settings


def run_shot_router(stage_input: StageInput) -> StageOutput:
    routes = build_shot_routes(stage_input.config, stage_input.payload)
    return StageOutput(
        "shot_router",
        "done",
        build_stage_payload(
            stage_input.payload,
            planner_key="shot_router",
            planner_value={"prompt": _route_policy_summary(stage_input.config)},
            workflow_key="shot_router",
            workflow_value={"decisions": _route_preview(routes)},
            render_updates={"clip_routes": routes},
            clip_routes=routes,
        ),
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


def build_shot_router_preview_payload(config: dict, payload: dict) -> dict:
    routes = build_shot_routes(config, payload)
    return build_stage_payload(
        payload,
        planner_key="shot_router",
        planner_value={"prompt": _route_policy_summary(config)},
        workflow_key="shot_router",
        workflow_value={"decisions": _route_preview(routes)},
        render_updates={"clip_routes": routes},
        clip_routes=routes,
    )
