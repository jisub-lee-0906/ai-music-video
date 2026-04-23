from __future__ import annotations

import json
from pathlib import Path

from ai_mv.core.contracts.stage_io import StageInput, StageOutput
from ai_mv.core.stages.review_stage import run_review_stage
from ai_mv.core.review.models import summarize_assembly_quality


_RESULT_KEYS = {
    "still_results": "still_results",
    "clip_results": "clip_results",
}


def run_rerender_review(stage_input: StageInput) -> StageOutput:
    rerender_results = stage_input.payload.get("rerender_results") if isinstance(stage_input.payload.get("rerender_results"), dict) else {}
    merged_payload = dict(stage_input.payload)
    merged_stills = _merge_asset_rows(stage_input.payload.get("still_results"), rerender_results.get("still_results"))
    merged_clips = _merge_asset_rows(stage_input.payload.get("clip_results"), rerender_results.get("clip_results"))
    merged_payload["still_results"] = merged_stills
    merged_payload["clip_results"] = merged_clips
    merged_payload["review_inputs"] = _merged_review_inputs(stage_input.payload.get("review_inputs"), rerender_results.get("review_inputs"))
    merged_payload["review_inputs"] = _drop_stale_manual_findings(
        merged_payload.get("review_inputs"),
        rerendered_shot_ids=_rerendered_shot_ids(rerender_results),
    )
    merged_payload["assembly_plan"] = _merged_assembly_plan(
        stage_input.payload.get("assembly_plan"),
        stage_input.payload.get("assembly_revision_result"),
    )
    rerender_final_video = (
        str(stage_input.payload.get("rerender_final_video", "")).strip()
        or str(stage_input.payload.get("final_video", "")).strip()
        or str(rerender_results.get("final_video", "")).strip()
    )
    if rerender_final_video:
        merged_payload["final_video"] = rerender_final_video
    rerender_music_file = str(stage_input.payload.get("music_file", "")).strip() or str(rerender_results.get("music_file", "")).strip()
    if rerender_music_file:
        merged_payload["music_file"] = rerender_music_file

    review_out = run_review_stage(StageInput(run_id=stage_input.run_id, config=stage_input.config, payload=merged_payload))
    out_payload = {
        "still_results": merged_stills,
        "clip_results": merged_clips,
        "rerender_review_report": dict(review_out.payload.get("review_report", {})),
    }
    if isinstance(merged_payload.get("assembly_plan"), dict):
        out_payload["assembly_plan"] = dict(merged_payload.get("assembly_plan", {}))
    if isinstance(merged_payload.get("review_inputs"), dict) and merged_payload.get("review_inputs"):
        out_payload["review_inputs"] = dict(merged_payload["review_inputs"])
    review_action = str(stage_input.payload.get("review_action", "")).strip() or str(rerender_results.get("review_action", "")).strip()
    if review_action:
        out_payload["review_action"] = review_action
    assembly_revision_result = stage_input.payload.get("assembly_revision_result")
    if isinstance(assembly_revision_result, dict) and assembly_revision_result:
        out_payload["assembly_revision_result"] = _annotate_assembly_revision_result(
            assembly_revision_result,
            prior_report=stage_input.payload.get("review_report"),
            rerender_report=out_payload["rerender_review_report"],
            prior_review_inputs=stage_input.payload.get("review_inputs"),
            merged_review_inputs=merged_payload.get("review_inputs"),
            planned_shot_ids=_targeted_or_planned_shot_ids(merged_payload, assembly_revision_result),
        )
    if rerender_final_video:
        out_payload["rerender_final_video"] = rerender_final_video
    return StageOutput(
        "rerender_review",
        "done",
        out_payload,
        list(review_out.artifacts),
    )



def _merge_asset_rows(existing_rows: object, fresh_rows: object) -> list[dict]:
    merged: list[dict] = []
    fresh_map = {
        str(row.get("shot_id", "")).strip(): row
        for row in fresh_rows if isinstance(fresh_rows, list)
        for _ in [0]
        if isinstance(row, dict) and str(row.get("shot_id", "")).strip()
    }
    for row in existing_rows if isinstance(existing_rows, list) else []:
        if not isinstance(row, dict):
            continue
        shot_id = str(row.get("shot_id", "")).strip()
        if shot_id and shot_id in fresh_map:
            continue
        merged.append(row)
    merged.extend(fresh_map.values())
    return merged



def _merged_review_inputs(existing_inputs: object, fresh_inputs: object) -> dict:
    existing = dict(existing_inputs) if isinstance(existing_inputs, dict) else {}
    fresh = dict(fresh_inputs) if isinstance(fresh_inputs, dict) else {}
    merged = dict(existing)
    for key, value in fresh.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = {**merged[key], **value}
        else:
            merged[key] = value
    return merged



def _drop_stale_manual_findings(review_inputs: object, *, rerendered_shot_ids: set[str]) -> dict:
    inputs = dict(review_inputs) if isinstance(review_inputs, dict) else {}
    combined_findings = _combined_quality_findings(inputs)
    filtered_findings = {
        shot_id: reasons
        for shot_id, reasons in combined_findings.items()
        if shot_id not in rerendered_shot_ids
    } if rerendered_shot_ids else combined_findings
    if combined_findings or "quality_findings" in inputs or "quality_findings_path" in inputs:
        inputs["quality_findings"] = filtered_findings
    inputs.pop("quality_findings_path", None)
    return inputs



def _combined_quality_findings(review_inputs: dict) -> dict[str, list[str]]:
    combined: dict[str, list[str]] = {}
    explicit_findings = review_inputs.get("quality_findings") if isinstance(review_inputs.get("quality_findings"), dict) else {}
    for shot_id, reasons in explicit_findings.items():
        _extend_unique(combined.setdefault(str(shot_id).strip(), []), reasons)
    path_findings = _load_quality_findings_from_path(review_inputs.get("quality_findings_path"))
    for shot_id, reasons in path_findings.items():
        _extend_unique(combined.setdefault(shot_id, []), reasons)
    return {shot_id: reasons for shot_id, reasons in combined.items() if shot_id and reasons}



def _load_quality_findings_from_path(path_value: object) -> dict[str, list[str]]:
    path_str = str(path_value or "").strip()
    if not path_str:
        return {}
    try:
        payload = json.loads(Path(path_str).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"invalid review quality findings file: {path_str}") from exc
    if isinstance(payload.get("review_inputs"), dict) and isinstance(payload["review_inputs"].get("quality_findings"), dict):
        payload = payload["review_inputs"].get("quality_findings")
    elif isinstance(payload.get("quality_findings"), dict):
        payload = payload.get("quality_findings")
    if not isinstance(payload, dict):
        return {}
    findings: dict[str, list[str]] = {}
    for shot_id, reasons in payload.items():
        normalized_shot_id = str(shot_id or "").strip()
        if not normalized_shot_id:
            continue
        _extend_unique(findings.setdefault(normalized_shot_id, []), reasons)
    return {shot_id: reasons for shot_id, reasons in findings.items() if reasons}



def _extend_unique(target: list[str], reasons: object) -> None:
    if not isinstance(reasons, (list, tuple, set)):
        return
    for reason in reasons:
        value = str(reason or "").strip()
        if value and value not in target:
            target.append(value)



def _rerendered_shot_ids(rerender_results: object) -> set[str]:
    if not isinstance(rerender_results, dict):
        return set()
    shot_ids: set[str] = set()
    for key in ("still_results", "clip_results"):
        for row in rerender_results.get(key, []) if isinstance(rerender_results.get(key), list) else []:
            if not isinstance(row, dict):
                continue
            if str(row.get("status", "")).strip().lower() not in {"done", "completed", "success"}:
                continue
            shot_id = str(row.get("shot_id", "")).strip()
            if shot_id:
                shot_ids.add(shot_id)
    return shot_ids



def _merged_assembly_plan(existing_plan: object, assembly_revision_result: object) -> dict:
    if isinstance(assembly_revision_result, dict) and isinstance(assembly_revision_result.get("revised_assembly_plan"), dict) and assembly_revision_result.get("revised_assembly_plan"):
        return dict(assembly_revision_result.get("revised_assembly_plan", {}))
    return dict(existing_plan) if isinstance(existing_plan, dict) else {}



def _annotate_assembly_revision_result(
    assembly_revision_result: dict,
    *,
    prior_report: object,
    rerender_report: object,
    prior_review_inputs: object,
    merged_review_inputs: object,
    planned_shot_ids: list[str],
) -> dict:
    annotated = dict(assembly_revision_result)
    prior_summary = prior_report.get("assembly_quality_summary") if isinstance(prior_report, dict) and isinstance(prior_report.get("assembly_quality_summary"), dict) else _summary_from_review_inputs(planned_shot_ids, prior_review_inputs)
    rerender_summary = rerender_report.get("assembly_quality_summary") if isinstance(rerender_report, dict) and isinstance(rerender_report.get("assembly_quality_summary"), dict) else _summary_from_review_inputs(planned_shot_ids, merged_review_inputs)
    improvement = {
        "targeted_issue_improved": _targeted_issue_improved(str(annotated.get("action", "")).strip(), prior_summary, rerender_summary),
        "before_repetitive_edit_risk_score": float(prior_summary.get("repetitive_edit_risk_score", 0.0) or 0.0),
        "after_repetitive_edit_risk_score": float(rerender_summary.get("repetitive_edit_risk_score", 0.0) or 0.0),
        "before_safe_editing_within_threshold": bool(prior_summary.get("safe_editing_within_threshold", False)),
        "after_safe_editing_within_threshold": bool(rerender_summary.get("safe_editing_within_threshold", False)),
        "before_transition_intentionality_score": float(prior_summary.get("transition_intentionality_score", 0.0) or 0.0),
        "after_transition_intentionality_score": float(rerender_summary.get("transition_intentionality_score", 0.0) or 0.0),
        "before_slideshow_risk_within_threshold": bool(prior_summary.get("slideshow_risk_within_threshold", False)),
        "after_slideshow_risk_within_threshold": bool(rerender_summary.get("slideshow_risk_within_threshold", False)),
    }
    annotated["improvement_summary"] = improvement
    return annotated



def _summary_from_review_inputs(planned_shot_ids: list[str], review_inputs: object) -> dict:
    inputs = dict(review_inputs) if isinstance(review_inputs, dict) else {}
    return summarize_assembly_quality(
        planned_shot_ids,
        inputs.get("edit_intent_by_shot") if isinstance(inputs.get("edit_intent_by_shot"), dict) else {},
        inputs.get("render_count_by_shot") if isinstance(inputs.get("render_count_by_shot"), dict) else {},
        inputs.get("render_priority_by_shot") if isinstance(inputs.get("render_priority_by_shot"), dict) else {},
        inputs.get("render_planning_by_shot") if isinstance(inputs.get("render_planning_by_shot"), dict) else {},
        inputs.get("cadence_profile_by_shot") if isinstance(inputs.get("cadence_profile_by_shot"), dict) else {},
        inputs.get("snap_unit_by_shot") if isinstance(inputs.get("snap_unit_by_shot"), dict) else {},
        inputs.get("trimmed_coverage_by_shot") if isinstance(inputs.get("trimmed_coverage_by_shot"), dict) else {},
    )



def _planned_shot_ids(payload: dict) -> list[str]:
    return [
        str(row.get("shot_id", "")).strip()
        for row in payload.get("shot_plan", []) if isinstance(payload.get("shot_plan"), list)
        for _ in [0]
        if isinstance(row, dict) and str(row.get("shot_id", "")).strip()
    ]



def _targeted_or_planned_shot_ids(payload: dict, assembly_revision_result: object) -> list[str]:
    targeted = [
        str(value).strip()
        for value in assembly_revision_result.get("target_shots", [])
        if isinstance(assembly_revision_result, dict) and isinstance(assembly_revision_result.get("target_shots"), list)
        and str(value).strip()
    ]
    return targeted or _planned_shot_ids(payload)



def _targeted_issue_improved(action: str, prior_summary: dict, rerender_summary: dict) -> bool:
    before_risk = float(prior_summary.get("repetitive_edit_risk_score", 0.0) or 0.0)
    after_risk = float(rerender_summary.get("repetitive_edit_risk_score", 0.0) or 0.0)
    before_safe = bool(prior_summary.get("safe_editing_within_threshold", False))
    after_safe = bool(rerender_summary.get("safe_editing_within_threshold", False))
    before_transition_intentionality = float(prior_summary.get("transition_intentionality_score", 0.0) or 0.0)
    after_transition_intentionality = float(rerender_summary.get("transition_intentionality_score", 0.0) or 0.0)
    before_slideshow_safe = bool(prior_summary.get("slideshow_risk_within_threshold", False))
    after_slideshow_safe = bool(rerender_summary.get("slideshow_risk_within_threshold", False))
    if action == "revise_assembly_weights_before_clip_rerender":
        return after_risk < before_risk or (after_safe and not before_safe)
    if action == "revise_transition_selection":
        return (
            after_transition_intentionality > before_transition_intentionality
            or (after_slideshow_safe and not before_slideshow_safe)
        )
    return after_risk < before_risk
