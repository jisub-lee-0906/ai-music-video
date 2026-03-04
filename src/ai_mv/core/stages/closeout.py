from __future__ import annotations

from ai_mv.core.contracts.stage_io import StageInput, StageOutput
from ai_mv.core.quality.quality_gate import evaluate_quality


def run_closeout(stage_input: StageInput) -> StageOutput:
    score = evaluate_quality(stage_input.payload)
    return StageOutput("closeout", "done", {"quality_score": score}, [])

