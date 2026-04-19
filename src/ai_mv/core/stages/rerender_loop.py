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
        merged_payload["rerender_outcome"] = {"attempted": False, "resolved": False, "exhausted": False}
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
    if isinstance(merged_payload.get("rerender_review_report"), dict):
        merged_payload["review_report"] = dict(merged_payload["rerender_review_report"])
    merged_payload["rerender_outcome"] = _rerender_outcome(merged_payload.get("review_report"))
    artifacts = [
        *[str(path) for path in executed.artifacts if str(path).strip()],
        *[str(path) for path in reviewed.artifacts if str(path).strip()],
    ]
    return StageOutput("rerender_loop", "done", merged_payload, artifacts)



def _rerender_outcome(review_report: object) -> dict[str, bool]:
    if not isinstance(review_report, dict):
        return {"attempted": True, "resolved": False, "exhausted": True}
    status = str(review_report.get("status", "")).strip()
    rerender_targets = review_report.get("rerender_targets")
    unresolved = status == "needs_rerender" or bool(rerender_targets)
    return {
        "attempted": True,
        "resolved": not unresolved,
        "exhausted": unresolved,
    }
