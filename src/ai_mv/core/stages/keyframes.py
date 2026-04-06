from __future__ import annotations

from ai_mv.core.contracts.stage_io import StageInput, StageOutput
from ai_mv.core.stages.flux2_ref_chain import _clip_routes_from_prompt_plan, build_flux2_ref_plan
from ai_mv.core.stages.tti_anchor import build_tti_anchor_plan
from ai_mv.engines.flux_2_dev_ref.runner import run_flux2_ref
from ai_mv.engines.flux_2_dev_tti.runner import run_tti


def run_keyframes(stage_input: StageInput) -> StageOutput:
    tti_plan = build_tti_anchor_plan(stage_input.config, stage_input.payload)
    anchors = run_tti(stage_input.config, tti_plan)
    master_anchor = str(anchors[0]["identity_anchor"]) if anchors else ""
    ref_plan = build_flux2_ref_plan(stage_input.config, {**stage_input.payload, "master_anchor": master_anchor})
    flux2_ref_images = run_flux2_ref(stage_input.config, ref_plan) if ref_plan["items"] else []
    clip_routes = _clip_routes_from_prompt_plan({**stage_input.payload, "master_anchor": master_anchor}, flux2_ref_images)
    return StageOutput(
        "keyframes",
        "done",
        {
            "anchors": anchors,
            "master_anchor": master_anchor,
            "flux2_ref_images": flux2_ref_images,
            "clip_routes": clip_routes,
            "keyframes": {
                "anchor_count": len(anchors),
                "reference_count": len(flux2_ref_images),
                "route_count": len(clip_routes),
            },
        },
        [],
    )
