from __future__ import annotations

from ai_mv.core.contracts.stage_io import StageInput, StageOutput
from ai_mv.core.stages.review_stage import run_review_stage
from ai_mv.utils.time_utils import ffprobe_duration


def run_review_outputs(stage_input: StageInput) -> StageOutput:
    return run_review_stage(stage_input, duration_fn=ffprobe_duration)
