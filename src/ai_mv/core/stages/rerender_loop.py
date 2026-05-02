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
    review_report = merged_payload.get("rerender_review_report") if isinstance(merged_payload.get("rerender_review_report"), dict) else None
    if review_report is not None:
        merged_payload["rerender_outcome"] = _rerender_outcome(
            review_report,
            assembly_revision_result=merged_payload.get("assembly_revision_result"),
        )
    else:
        merged_payload["rerender_outcome"] = _rerender_outcome(
            merged_payload.get("review_report"),
            assembly_revision_result=merged_payload.get("assembly_revision_result"),
        )

    final_video = str(merged_payload.get("final_video", "")).strip()
    if final_video:
        merged_payload["rerender_final_video"] = final_video
        merged_payload.pop("final_video", None)
    merged_payload.pop("review_report", None)
    artifacts = [
        *[str(path) for path in executed.artifacts if str(path).strip()],
        *[str(path) for path in reviewed.artifacts if str(path).strip()],
    ]
    return StageOutput("rerender_loop", "done", merged_payload, artifacts)



def _rerender_outcome(review_report: object, *, assembly_revision_result: object = None) -> dict[str, bool]:
    if not isinstance(review_report, dict):
        return {"attempted": True, "resolved": False, "exhausted": True}
    status = str(review_report.get("status", "")).strip()
    rerender_targets = review_report.get("rerender_targets")
    rerender_payloads = review_report.get("rerender_execution_payloads")
    unresolved = status == "needs_rerender" or bool(rerender_targets) or bool(rerender_payloads)
    if unresolved and _assembly_coverage_revision_resolved_clone_tail(review_report, assembly_revision_result):
        unresolved = False
    return {
        "attempted": True,
        "resolved": not unresolved,
        "exhausted": unresolved,
    }


def _assembly_coverage_revision_resolved_clone_tail(review_report: dict, assembly_revision_result: object) -> bool:
    if not isinstance(assembly_revision_result, dict):
        return False
    if str(assembly_revision_result.get("status", "")).strip() != "applied":
        return False
    if str(assembly_revision_result.get("action", "")).strip() != "revise_assembly_coverage_before_sync_pad":
        return False
    if not str(assembly_revision_result.get("output_final_video", "")).strip():
        return False
    rerender_targets = review_report.get("rerender_targets")
    rerender_payloads = review_report.get("rerender_execution_payloads")
    if rerender_targets or rerender_payloads:
        return False
    blocking_checks = review_report.get("blocking_checks") if isinstance(review_report.get("blocking_checks"), dict) else {}
    return bool(blocking_checks.get("sync_clone_tail_within_threshold", False))
