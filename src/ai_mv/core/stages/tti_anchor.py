from __future__ import annotations

from ai_mv.core.contracts.stage_io import StageInput, StageOutput
from ai_mv.engines.flux_1_dev_tti.planner import build_tti_plan
from ai_mv.engines.flux_1_dev_tti.runner import run_tti


def run_tti_anchor(stage_input: StageInput) -> StageOutput:
    plan = build_tti_plan(stage_input.config, stage_input.payload)
    anchors = run_tti(stage_input.config, plan)
    return StageOutput("tti_anchor", "done", {"anchors": anchors}, [])

