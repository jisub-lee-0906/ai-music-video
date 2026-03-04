from __future__ import annotations

from ai_mv.core.contracts.stage_io import StageInput, StageOutput
from ai_mv.engines.wan_2_2_flf2v.planner import build_wan_plan
from ai_mv.engines.wan_2_2_flf2v.runner import run_wan


def run_wan_interpolation(stage_input: StageInput) -> StageOutput:
    plan = build_wan_plan(stage_input.config, stage_input.payload)
    clips = run_wan(stage_input.config, plan)
    return StageOutput("wan_interpolation", "done", {"clips": clips}, [])

