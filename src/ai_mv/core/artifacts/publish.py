from __future__ import annotations

from ai_mv.core.artifacts.manifest import write_manifest
from ai_mv.core.artifacts.provenance import dedupe_preserve_order
from ai_mv.core.artifacts.run_summary import write_run_summary
from ai_mv.core.artifacts.schema import artifact_schema_version
from ai_mv.core.artifacts.summary_fields import derive_summary_fields


def _story_contract_summary(shot_plan: object) -> dict:
    shots = [row for row in shot_plan if isinstance(row, dict)] if isinstance(shot_plan, list) else []
    required = {
        "why_this_shot",
        "protagonist_action",
        "section_alignment",
        "progression_from_previous",
        "visual_payoff",
        "anti_repetition_constraint",
    }
    complete: list[dict] = []
    missing_ids: list[str] = []
    for row in shots:
        contract = row.get("story_contract") if isinstance(row.get("story_contract"), dict) else {}
        has_all = all(str(contract.get(key, "")).strip() for key in required)
        if has_all:
            complete.append(row)
        else:
            shot_id = str(row.get("shot_id", "")).strip()
            if shot_id:
                missing_ids.append(shot_id)
    sections = dedupe_preserve_order(str(row.get("section_type", "")).strip() for row in complete if str(row.get("section_type", "")).strip())
    action_samples = [
        str(row.get("story_contract", {}).get("protagonist_action", "")).strip()
        for row in complete[:6]
        if isinstance(row.get("story_contract"), dict) and str(row.get("story_contract", {}).get("protagonist_action", "")).strip()
    ]
    return {
        "story_contract_shot_count": len(complete),
        "story_contract_total_shot_count": len(shots),
        "story_contract_coverage_ratio": round((len(complete) / len(shots)) if shots else 0.0, 3),
        "story_contract_sections": sections,
        "story_contract_missing_shot_ids": missing_ids,
        "story_contract_action_samples": action_samples,
    }


def write_pipeline_artifacts(state: dict, payload: dict, config: dict) -> None:
    write_manifest(state, payload)
    rerender_escalation = payload.get("rerender_escalation") if isinstance(payload.get("rerender_escalation"), dict) else {}
    summary_by_shot = rerender_escalation.get("summary_by_shot") if isinstance(rerender_escalation.get("summary_by_shot"), list) else []
    escalation_artifacts = rerender_escalation.get("artifacts") if isinstance(rerender_escalation.get("artifacts"), dict) else {}
    escalation_actions = [
        str(row.get("recommended_action", "")).strip()
        for row in summary_by_shot
        if isinstance(row, dict) and str(row.get("recommended_action", "")).strip()
    ]
    escalation_priorities = [
        int(row.get("priority_score", 0) or 0)
        for row in summary_by_shot
        if isinstance(row, dict)
    ]
    escalation_reason_codes = [
        str(reason).strip()
        for row in summary_by_shot
        if isinstance(row, dict)
        for reason in row.get("reason_codes", []) if str(reason).strip()
    ]
    escalation_shot_ids = [
        str(row.get("shot_id", "")).strip()
        for row in summary_by_shot
        if isinstance(row, dict) and str(row.get("shot_id", "")).strip()
    ]
    escalation_material_ids = [
        str(row.get("material_id", "")).strip()
        for row in summary_by_shot
        if isinstance(row, dict) and str(row.get("material_id", "")).strip()
    ]
    escalation_section_ids = [
        str(row.get("section_id", "")).strip()
        for row in summary_by_shot
        if isinstance(row, dict) and str(row.get("section_id", "")).strip()
    ]
    escalation_reference_modes = [
        str(reference_context.get("reference_mode", "")).strip()
        for row in summary_by_shot
        if isinstance(row, dict)
        for reference_context in [row.get("reference_context")]
        if isinstance(reference_context, dict) and str(reference_context.get("reference_mode", "")).strip()
    ]
    escalation_reference_source_shot_ids = [
        str(reference_context.get("reference_source_shot_id", "")).strip()
        for row in summary_by_shot
        if isinstance(row, dict)
        for reference_context in [row.get("reference_context")]
        if isinstance(reference_context, dict) and str(reference_context.get("reference_source_shot_id", "")).strip()
    ]
    escalation_reference_labels_by_shot = [
        f"{shot_id}: {reference_summary_label}"
        for row in summary_by_shot
        if isinstance(row, dict)
        for shot_id in [str(row.get("shot_id", "")).strip()]
        for reference_summary_label in [str(row.get("reference_summary_label", "")).strip()]
        if shot_id and reference_summary_label
    ]
    escalation_reference_summary_labels = [
        str(row.get("reference_summary_label", "")).strip()
        for row in summary_by_shot
        if isinstance(row, dict) and str(row.get("reference_summary_label", "")).strip()
    ]
    summary_fields = derive_summary_fields(payload)
    anchor_results = [row for row in payload.get("anchor_results", []) if isinstance(row, dict)]
    anchor_result_ids = [str(row.get("anchor_id", "")).strip() for row in anchor_results if str(row.get("anchor_id", "")).strip()]
    anchor_result_image_paths = [str(row.get("image", "")).strip() for row in anchor_results if str(row.get("image", "")).strip()]
    anchor_result_workflow_targets = [str(row.get("workflow_target", "")).strip() for row in anchor_results if str(row.get("workflow_target", "")).strip()]
    review_report = payload.get("review_report") if isinstance(payload.get("review_report"), dict) else {}
    review_scores = review_report.get("scores") if isinstance(review_report.get("scores"), dict) else {}
    review_severity = review_report.get("severity") if isinstance(review_report.get("severity"), dict) else {}
    review_signal_buckets_raw = review_report.get("review_signal_buckets") if isinstance(review_report.get("review_signal_buckets"), dict) else {}
    review_signal_buckets = {
        str(bucket_name).strip(): {
            "passed": bool(bucket.get("passed", False)),
            "failed_checks": [str(value).strip() for value in bucket.get("failed_checks", []) if str(value).strip()]
            if isinstance(bucket.get("failed_checks"), list) else [],
        }
        for bucket_name, bucket in review_signal_buckets_raw.items()
        if str(bucket_name).strip() and isinstance(bucket, dict)
    }
    review_signal_bucket_failed_checks = dedupe_preserve_order(
        failed_check
        for bucket in review_signal_buckets.values()
        for failed_check in bucket.get("failed_checks", [])
    )
    sync_repair_summary = payload.get("sync_repair_summary") if isinstance(payload.get("sync_repair_summary"), dict) else {}
    story_contract_summary = _story_contract_summary(payload.get("shot_plan"))
    summary = {
        "run_id": state["run_id"],
        "scope": str(state.get("scope", "run")),
        "status": str(state.get("status", "")),
        "current_stage": str(state.get("current_stage", "")),
        "failure_reason": str(state.get("failure_reason", "")),
        "completed_stages": list(state.get("completed_stages", [])),
        "schema_version": artifact_schema_version(),
        "concept_text": str(payload.get("concept_text", "")).strip(),
        **story_contract_summary,
        **summary_fields,
        "final_video": str(payload.get("final_video", "")).strip(),
        "music_file": str(payload.get("music_file", "")).strip(),
        "anchor_result_count": len(anchor_results),
        "anchor_result_ids": anchor_result_ids,
        "anchor_result_image_paths": anchor_result_image_paths,
        "anchor_result_workflow_targets": anchor_result_workflow_targets,
        "anchor_result_unique_workflow_targets": dedupe_preserve_order(anchor_result_workflow_targets),
        "review_status": str(review_report.get("status", "")).strip(),
        "overall_status": str(review_report.get("overall_status", "")).strip(),
        "publishability_tier": str(review_report.get("publishability_tier", "")).strip(),
        "recommended_next_action": str(review_report.get("recommended_next_action", "")).strip(),
        "overall_score": float(review_scores.get("overall", 0.0) or 0.0),
        "technical_completion_score": float(review_scores.get("technical_completion", 0.0) or 0.0),
        "material_quality_score": float(review_scores.get("material_quality", 0.0) or 0.0),
        "final_mv_quality_score": float(review_scores.get("final_mv_quality", 0.0) or 0.0),
        "review_severity": {str(key).strip(): str(value).strip() for key, value in review_severity.items() if str(key).strip()},
        "review_severity_drift": str(review_severity.get("drift", "")).strip(),
        "review_severity_coverage": str(review_severity.get("coverage", "")).strip(),
        "review_severity_visual_quality": str(review_severity.get("visual_quality", "")).strip(),
        "review_severity_assembly_quality": str(review_severity.get("assembly_quality", "")).strip(),
        "review_signal_buckets": review_signal_buckets,
        "review_signal_bucket_failed_checks": review_signal_bucket_failed_checks,
        "sync_repair_strategy": str(sync_repair_summary.get("repair_strategy", "")).strip(),
        "sync_repair_clone_tail_sec": float(sync_repair_summary.get("clone_tail_sec", 0.0) or 0.0),
        "sync_repair_clone_tail_ratio": float(sync_repair_summary.get("clone_tail_ratio", 0.0) or 0.0),
        "sync_repair_clone_tail_excessive": bool(sync_repair_summary.get("clone_tail_excessive", False)),
        "rerender_target_count": len(review_report.get("rerender_targets", [])),
        "rerender_escalation_status": str(rerender_escalation.get("status", "")).strip(),
        "rerender_escalation_shot_count": int(rerender_escalation.get("shot_count", 0) or 0),
        "rerender_escalation_reviewer_summary": str(rerender_escalation.get("reviewer_summary", "")).strip(),
        "rerender_escalation_shot_ids": escalation_shot_ids,
        "rerender_escalation_material_ids": escalation_material_ids,
        "rerender_escalation_section_ids": escalation_section_ids,
        "rerender_escalation_unique_material_ids": dedupe_preserve_order(escalation_material_ids),
        "rerender_escalation_unique_section_ids": dedupe_preserve_order(escalation_section_ids),
        "rerender_escalation_actions": escalation_actions,
        "rerender_escalation_max_priority": max(escalation_priorities) if escalation_priorities else 0,
        "rerender_escalation_unique_actions": sorted(set(escalation_actions)),
        "rerender_escalation_reason_codes": escalation_reason_codes,
        "rerender_escalation_unique_reason_codes": sorted(set(escalation_reason_codes)),
        "rerender_escalation_reference_modes": escalation_reference_modes,
        "rerender_escalation_unique_reference_modes": dedupe_preserve_order(escalation_reference_modes),
        "rerender_escalation_reference_source_shot_ids": escalation_reference_source_shot_ids,
        "rerender_escalation_unique_reference_source_shot_ids": dedupe_preserve_order(escalation_reference_source_shot_ids),
        "rerender_escalation_reference_labels_by_shot": escalation_reference_labels_by_shot,
        "rerender_escalation_unique_reference_summary_labels": dedupe_preserve_order(escalation_reference_summary_labels),
        "rerender_escalation_artifact_keys": sorted(str(key).strip() for key in escalation_artifacts.keys() if str(key).strip()),
        "rerender_escalation_review_packet_manifest": str(escalation_artifacts.get("review_packet_manifest", "")).strip(),
        "rerender_escalation_quality_findings_path": str(escalation_artifacts.get("quality_findings", "")).strip(),
        "rerender_escalation_reviewer_notes_path": str(escalation_artifacts.get("reviewer_notes", "")).strip(),
    }
    write_run_summary(state, summary)
