from __future__ import annotations

from ai_mv.core.contracts.stage_io import StageInput, StageOutput
from ai_mv.core.stages.execute_rerender import run_execute_rerender
from ai_mv.core.stages.prepare_rerender import run_prepare_rerender
from ai_mv.core.stages.repair_rerender_prompts import run_repair_rerender_prompts
from ai_mv.core.stages.rerender_review import run_rerender_review


def run_rerender_loop(stage_input: StageInput) -> StageOutput:
    merged_payload = dict(stage_input.payload)
    artifacts: list[str] = []
    attempts = 0
    max_attempts = _coverage_repair_max_attempts(stage_input)

    while True:
        prepared = run_prepare_rerender(StageInput(run_id=stage_input.run_id, config=stage_input.config, payload=merged_payload))
        merged_payload.update(dict(prepared.payload))
        stage_sequence = merged_payload.get("rerender_stage_sequence") if isinstance(merged_payload.get("rerender_stage_sequence"), list) else []
        if not stage_sequence:
            if attempts == 0:
                merged_payload["rerender_outcome"] = {"attempted": False, "resolved": False, "exhausted": False}
            break

        attempts += 1
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
        artifacts.extend(str(path) for path in executed.artifacts if str(path).strip())
        artifacts.extend(str(path) for path in reviewed.artifacts if str(path).strip())
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

        if not _should_repeat_coverage_repair(merged_payload, attempts=attempts, max_attempts=max_attempts):
            break

    final_video = str(merged_payload.get("final_video", "")).strip()
    if final_video:
        merged_payload["rerender_final_video"] = final_video
        merged_payload.pop("final_video", None)
    merged_payload.pop("review_report", None)
    if attempts:
        merged_payload["coverage_repair_loop"] = {
            "attempts": attempts,
            "max_attempts": max_attempts,
            "exhausted": _coverage_repair_still_required(merged_payload),
        }
    return StageOutput("rerender_loop", "done", merged_payload, artifacts)


def _coverage_repair_max_attempts(stage_input: StageInput) -> int:
    for value in (
        stage_input.payload.get("coverage_repair_max_attempts"),
        stage_input.config.get("coverage_repair_max_attempts") if isinstance(stage_input.config, dict) else None,
        stage_input.payload.get("rerender_max_attempts"),
        stage_input.config.get("rerender_max_attempts") if isinstance(stage_input.config, dict) else None,
    ):
        try:
            attempts = int(value)
        except (TypeError, ValueError):
            continue
        if attempts > 0:
            return attempts
    return 1


def _should_repeat_coverage_repair(payload: dict, *, attempts: int, max_attempts: int) -> bool:
    if attempts >= max_attempts:
        return False
    outcome = payload.get("rerender_outcome") if isinstance(payload.get("rerender_outcome"), dict) else {}
    if not bool(outcome.get("exhausted", False)):
        return False
    return _coverage_repair_still_required(payload)


def _coverage_repair_still_required(payload: dict) -> bool:
    assembly_plan = payload.get("assembly_plan") if isinstance(payload.get("assembly_plan"), dict) else {}
    coverage_summary = assembly_plan.get("coverage_summary") if isinstance(assembly_plan.get("coverage_summary"), dict) else {}
    repair_plan = assembly_plan.get("coverage_repair_plan") if isinstance(assembly_plan.get("coverage_repair_plan"), dict) else {}
    repair_shots = repair_plan.get("repair_shots") if isinstance(repair_plan.get("repair_shots"), list) else []
    return bool(
        str(coverage_summary.get("status", "")).strip() == "insufficient_raw_coverage"
        and str(repair_plan.get("status", "")).strip() == "repair_required"
        and any(isinstance(row, dict) and str(row.get("shot_id", "")).strip() for row in repair_shots)
    )


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
