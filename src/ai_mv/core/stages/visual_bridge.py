from __future__ import annotations

from ai_mv.core.contracts.stage_io import StageInput, StageOutput
from ai_mv.engines.visual_bridge.planner import build_visual_brief


def run_visual_bridge(stage_input: StageInput) -> StageOutput:
    brief = build_visual_brief(stage_input.config, stage_input.payload)
    return StageOutput("visual_bridge", "done", {"visual_brief": brief}, [])
