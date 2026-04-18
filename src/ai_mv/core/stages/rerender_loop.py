from __future__ import annotations

from ai_mv.core.contracts.stage_io import StageInput, StageOutput
from ai_mv.core.stages.execute_rerender import run_execute_rerender
from ai_mv.core.stages.prepare_rerender import run_prepare_rerender
from ai_mv.core.stages.repair_rerender_prompts import run_repair_rerender_prompts
from ai_mv.core.stages.rerender_review import run_rerender_review


def run_rerender_loop(stage_input: StageInput) -> StageOutput:
    base_payload = dict(stage_input.payload)

    prepared = run_prepare_rerender(StageInput(run_id=stage_input.run_id, config=stage_input.config, payload=base_payload))
    merged_payload = {**base_payload, **dict(prepared.payload)}
    stage_sequence = merged_payload.get("rerender_stage_sequence") if isinstance(merged_payload.get("rerender_stage_sequence"), list) else []
    if not stage_sequence:
        return StageOutput("rerender_loop", "done", merged_payload, [])

    repaired = run_repair_rerender_prompts(
        StageInput(run_id=stage_input.run_id, config=stage_input.config, payload=merged_payload)
    )
    merged_payload.update(dict(repaired.payload))

    executed = run_execute_rerender(
        StageInput(run_id=stage_input.run_id, config=stage_input.config, payload=merged_payload)
    )
    merged_payload.update(dict(executed.payload))

    reviewed = run_rerender_review(
        StageInput(run_id=stage_input.run_id, config=stage_input.config, payload=merged_payload)
    )
    merged_payload.update(dict(reviewed.payload))
    return StageOutput("rerender_loop", "done", merged_payload, list(reviewed.artifacts))
