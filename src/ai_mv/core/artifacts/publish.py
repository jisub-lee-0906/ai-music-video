from __future__ import annotations

import math

from ai_mv.core.artifacts.manifest import write_manifest
from ai_mv.core.artifacts.run_summary import write_run_summary
from ai_mv.core.artifacts.schema import artifact_schema_version


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        parsed = float(value)
    except Exception:
        return default
    return parsed if math.isfinite(parsed) else default


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
    style_resolution = payload.get("style_resolution") if isinstance(payload.get("style_resolution"), dict) else {}
    review_report = payload.get("review_report") if isinstance(payload.get("review_report"), dict) else {}
    assembly_revision_summary = review_report.get("assembly_revision_summary") if isinstance(review_report.get("assembly_revision_summary"), dict) else {}
    summary = {
        "run_id": state["run_id"],
        "scope": str(state.get("scope", "run")),
        "status": str(state.get("status", "")),
        "current_stage": str(state.get("current_stage", "")),
        "failure_reason": str(state.get("failure_reason", "")),
        "completed_stages": list(state.get("completed_stages", [])),
        "schema_version": artifact_schema_version(),
        "concept_text": str(payload.get("concept_text", "")).strip(),
        "style_name": str(style_resolution.get("style_name") or payload.get("style_name", "")).strip(),
        "style_selection_source": str(style_resolution.get("selection_source", "")).strip(),
        "style_selection_stability": str(style_resolution.get("selection_stability", "")).strip(),
        "style_selection_confidence": _safe_float(style_resolution.get("confidence", 0.0), 0.0),
        "final_video": str(payload.get("final_video", "")).strip(),
        "music_file": str(payload.get("music_file", "")).strip(),
        "review_status": str(review_report.get("status", "")).strip(),
        "rerender_target_count": len(review_report.get("rerender_targets", [])),
        "assembly_revision_present": bool(assembly_revision_summary.get("present", False)),
        "assembly_revision_action": str(assembly_revision_summary.get("action", "")).strip(),
        "assembly_revision_target": str(assembly_revision_summary.get("target", "")).strip(),
        "assembly_revision_final_video": str(assembly_revision_summary.get("final_video", "")).strip(),
        "assembly_revision_music_file": str(assembly_revision_summary.get("music_file", "")).strip(),
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
