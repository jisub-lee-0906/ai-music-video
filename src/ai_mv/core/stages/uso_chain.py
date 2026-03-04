from __future__ import annotations

from ai_mv.core.contracts.stage_io import StageInput, StageOutput
from ai_mv.engines.flux_1_dev_uso.planner import build_uso_plan
from ai_mv.engines.flux_1_dev_uso.runner import run_uso


def run_uso_chain(stage_input: StageInput) -> StageOutput:
    plan = build_uso_plan(stage_input.config, stage_input.payload)
    uso_images = run_uso(stage_input.config, plan)
    return StageOutput("uso_chain", "done", {"uso_images": uso_images}, [])

