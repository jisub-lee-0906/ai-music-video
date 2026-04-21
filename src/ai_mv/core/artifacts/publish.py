from __future__ import annotations

from ai_mv.core.artifacts.manifest import write_manifest
from ai_mv.core.artifacts.run_summary import write_run_summary
from ai_mv.core.artifacts.schema import artifact_schema_version
from ai_mv.core.artifacts.summary_fields import derive_summary_fields


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
    summary_fields = derive_summary_fields(payload)
    review_report = payload.get("review_report") if isinstance(payload.get("review_report"), dict) else {}
    review_scores = review_report.get("scores") if isinstance(review_report.get("scores"), dict) else {}
    summary = {
        "run_id": state["run_id"],
        "scope": str(state.get("scope", "run")),
        "status": str(state.get("status", "")),
        "current_stage": str(state.get("current_stage", "")),
        "failure_reason": str(state.get("failure_reason", "")),
        "completed_stages": list(state.get("completed_stages", [])),
        "schema_version": artifact_schema_version(),
        "concept_text": str(payload.get("concept_text", "")).strip(),
        **summary_fields,
        "final_video": str(payload.get("final_video", "")).strip(),
        "music_file": str(payload.get("music_file", "")).strip(),
        "review_status": str(review_report.get("status", "")).strip(),
        "overall_status": str(review_report.get("overall_status", "")).strip(),
        "publishability_tier": str(review_report.get("publishability_tier", "")).strip(),
        "recommended_next_action": str(review_report.get("recommended_next_action", "")).strip(),
        "overall_score": float(review_scores.get("overall", 0.0) or 0.0),
        "technical_completion_score": float(review_scores.get("technical_completion", 0.0) or 0.0),
        "material_quality_score": float(review_scores.get("material_quality", 0.0) or 0.0),
        "final_mv_quality_score": float(review_scores.get("final_mv_quality", 0.0) or 0.0),
        "rerender_target_count": len(review_report.get("rerender_targets", [])),
        "rerender_escalation_status": str(rerender_escalation.get("status", "")).strip(),
        "rerender_escalation_shot_count": int(rerender_escalation.get("shot_count", 0) or 0),
        "rerender_escalation_reviewer_summary": str(rerender_escalation.get("reviewer_summary", "")).strip(),
        "rerender_escalation_shot_ids": [
            str(row.get("shot_id", "")).strip()
            for row in summary_by_shot
            if isinstance(row, dict) and str(row.get("shot_id", "")).strip()
        ],
        "rerender_escalation_actions": escalation_actions,
        "rerender_escalation_max_priority": max(escalation_priorities) if escalation_priorities else 0,
        "rerender_escalation_unique_actions": sorted(set(escalation_actions)),
        "rerender_escalation_reason_codes": escalation_reason_codes,
        "rerender_escalation_unique_reason_codes": sorted(set(escalation_reason_codes)),
        "rerender_escalation_artifact_keys": sorted(str(key).strip() for key in escalation_artifacts.keys() if str(key).strip()),
        "rerender_escalation_review_packet_manifest": str(escalation_artifacts.get("review_packet_manifest", "")).strip(),
        "rerender_escalation_quality_findings_path": str(escalation_artifacts.get("quality_findings", "")).strip(),
        "rerender_escalation_reviewer_notes_path": str(escalation_artifacts.get("reviewer_notes", "")).strip(),
    }
    write_run_summary(state, summary)
