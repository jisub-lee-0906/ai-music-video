from __future__ import annotations

import math

from ai_mv.core.review.benchmark_dimensions import summarize_benchmark_dimensions
from ai_mv.core.review.publishability import classify_rerender_target, summarize_publishability
from ai_mv.core.review.quality_signals import build_quality_signals
from ai_mv.core.review.rerender_policy import rerender_priority_score
from ai_mv.core.review.signal_buckets import summarize_review_signal_buckets



def build_shot_quality_scores(
    *,
    planned_shot_ids: list[str],
    still_status: dict[str, bool],
    clip_status: dict[str, bool],
    rerender_reasons: dict[str, list[str]],
) -> dict[str, float]:
    shot_scores: dict[str, float] = {}
    priority_scores = {shot_id: rerender_priority_score(reasons) for shot_id, reasons in rerender_reasons.items()}
    for shot_id in planned_shot_ids:
        score = 100.0
        if not still_status.get(shot_id, False):
            score -= 25.0
        if not clip_status.get(shot_id, False):
            score -= 35.0
        score -= float(priority_scores.get(shot_id, 0))
        shot_scores[shot_id] = round(max(0.0, min(100.0, score)), 2)
    return shot_scores



def build_rerender_plan(*, rerender_targets: list[str], rerender_reasons: dict[str, list[str]]) -> list[dict[str, object]]:
    plan: list[dict[str, object]] = []
    reasons_map = rerender_reasons if isinstance(rerender_reasons, dict) else {}
    for shot_id in rerender_targets:
        normalized_shot_id = str(shot_id or "").strip()
        if not normalized_shot_id:
            continue
        reason_codes = [
            str(reason).strip()
            for reason in reasons_map.get(normalized_shot_id, [])
            if str(reason).strip()
        ]
        if not reason_codes:
            continue
        classification = classify_rerender_target(reason_codes)
        plan.append(
            {
                "shot_id": normalized_shot_id,
                "reason_codes": reason_codes,
                "priority_score": rerender_priority_score(reason_codes),
                "bucket": classification["bucket"],
                "recommended_action": classification["recommended_action"],
                "rerender_prescription": classification["rerender_prescription"],
            }
        )
    return sorted(plan, key=lambda item: (-int(item["priority_score"]), str(item["shot_id"])))



def build_rerender_payload(rerender_plan: list[dict[str, object]]) -> list[dict[str, object]]:
    payload: list[dict[str, object]] = []
    for item in rerender_plan if isinstance(rerender_plan, list) else []:
        if not isinstance(item, dict):
            continue
        prescription = item.get("rerender_prescription") if isinstance(item.get("rerender_prescription"), dict) else {}
        payload.append(
            {
                "shot_id": str(item.get("shot_id", "")).strip(),
                "quality_findings": [str(reason).strip() for reason in item.get("reason_codes", []) if str(reason).strip()],
                "rerender_stage": prescription.get("stage_focus"),
                "workflow_focus": list(prescription.get("workflow_focus") or []) if isinstance(prescription.get("workflow_focus"), list) else prescription.get("workflow_focus"),
                "prompt_contract_focus": list(prescription.get("prompt_contract_focus") or []) if isinstance(prescription.get("prompt_contract_focus"), list) else [],
                "recommended_action": str(item.get("recommended_action", "")).strip(),
                "fix_strategy": prescription.get("fix_strategy"),
            }
        )
    return payload



def build_rerender_execution_payloads(
    *,
    rerender_payload: list[dict[str, object]],
    shot_plan: list[dict],
    render_plan: list[dict],
    still_results: list[dict],
    music_file: str,
    final_video_path: str = "",
) -> list[dict[str, object]]:
    shot_map = {str(row.get("shot_id", "")).strip(): row for row in shot_plan if isinstance(row, dict)}
    render_map = {str(row.get("shot_id", "")).strip(): row for row in render_plan if isinstance(row, dict)}
    still_map = {str(row.get("shot_id", "")).strip(): row for row in still_results if isinstance(row, dict)}
    execution_payloads: list[dict[str, object]] = []
    normalized_music_file = str(music_file or "").strip()
    normalized_final_video = str(final_video_path or "").strip()
    for item in rerender_payload if isinstance(rerender_payload, list) else []:
        if not isinstance(item, dict):
            continue
        shot_id = str(item.get("shot_id", "")).strip()
        if not shot_id:
            continue
        stage_focus = str(item.get("rerender_stage", "")).strip()
        shot_row = shot_map.get(shot_id)
        render_row = render_map.get(shot_id)
        stage_payloads: dict[str, dict[str, object]] = {}
        if stage_focus in {"stills", "stills_then_clips"}:
            stage_payloads["stills"] = {
                "shot_plan": [shot_row] if isinstance(shot_row, dict) else [],
                "render_plan": [render_row] if isinstance(render_row, dict) else [],
            }
        if stage_focus in {"clips", "stills_then_clips"}:
            still_rows: list[dict] = []
            for dep_shot_id in _clip_dependency_shot_ids(shot_row, render_row):
                row = still_map.get(dep_shot_id)
                if isinstance(row, dict):
                    still_rows.append(row)
            stage_payloads["clips"] = {
                "shot_plan": [shot_row] if isinstance(shot_row, dict) else [],
                "render_plan": [render_row] if isinstance(render_row, dict) else [],
                "still_results": still_rows,
                "music_file": normalized_music_file,
            }
        if stage_focus == "review":
            stage_payloads["review"] = {
                "final_video": normalized_final_video,
                "music_file": normalized_music_file,
                "recommended_action": str(item.get("recommended_action", "")).strip(),
            }
        execution_payloads.append(
            {
                "shot_id": shot_id,
                "recommended_action": str(item.get("recommended_action", "")).strip(),
                "rerender_stage": stage_focus,
                "stage_payloads": stage_payloads,
            }
        )
    return execution_payloads



def _clip_dependency_shot_ids(shot_row: dict | None, render_row: dict | None) -> list[str]:
    shot_ids: list[str] = []
    primary = str((shot_row or {}).get("shot_id", "") or (render_row or {}).get("shot_id", "")).strip()
    if primary:
        shot_ids.append(primary)
    bridge_target = str((render_row or {}).get("still_b", "") or (shot_row or {}).get("bridge_to_shot_id", "")).strip()
    if bridge_target and bridge_target not in shot_ids:
        shot_ids.append(bridge_target)
    return shot_ids



def summarize_edit_intent(edit_intent_by_shot: dict[str, dict] | None) -> dict:
    data = edit_intent_by_shot if isinstance(edit_intent_by_shot, dict) else {}
    high_priority_shots: list[str] = []
    section_emphasis_counts: dict[str, int] = {}
    for shot_id, row in data.items():
        if not isinstance(row, dict):
            continue
        normalized_shot_id = str(shot_id or "").strip()
        if not normalized_shot_id:
            continue
        if str(row.get("edit_priority", "")).strip() == "high":
            high_priority_shots.append(normalized_shot_id)
        emphasis = str(row.get("section_emphasis", "")).strip()
        if emphasis:
            section_emphasis_counts[emphasis] = int(section_emphasis_counts.get(emphasis, 0)) + 1
    return {
        "shot_count": len([shot_id for shot_id, row in data.items() if str(shot_id or "").strip() and isinstance(row, dict)]),
        "high_priority_shots": sorted(high_priority_shots),
        "section_emphasis_counts": section_emphasis_counts,
    }



def build_mv_intent_checks(edit_intent_summary: dict | None) -> dict[str, bool]:
    summary = edit_intent_summary if isinstance(edit_intent_summary, dict) else {}
    emphasis_counts = summary.get("section_emphasis_counts") if isinstance(summary.get("section_emphasis_counts"), dict) else {}
    high_priority_shots = summary.get("high_priority_shots") if isinstance(summary.get("high_priority_shots"), list) else []
    return {
        "hook_shot_present": bool(high_priority_shots),
        "section_emphasis_present": bool(emphasis_counts),
        "chorus_emphasis_present": bool(emphasis_counts.get("chorus_push", 0)),
        "bridge_emphasis_present": bool(emphasis_counts.get("bridge_contrast", 0)),
    }



def summarize_assembly_quality(
    *,
    planned_shot_ids: list[str],
    edit_intent_by_shot: dict[str, dict] | None,
    render_count_by_shot: dict[str, int] | None,
    render_priority_by_shot: dict[str, float] | None,
    render_planning_by_shot: dict[str, dict] | None,
) -> dict:
    edit_data = edit_intent_by_shot if isinstance(edit_intent_by_shot, dict) else {}
    render_counts = render_count_by_shot if isinstance(render_count_by_shot, dict) else {}
    render_priorities = render_priority_by_shot if isinstance(render_priority_by_shot, dict) else {}
    render_planning = render_planning_by_shot if isinstance(render_planning_by_shot, dict) else {}

    normalized_planned_shot_ids = {str(shot_id).strip() for shot_id in planned_shot_ids if str(shot_id or "").strip()}
    normalized_edit_data = {
        str(shot_id).strip(): row
        for shot_id, row in edit_data.items()
        if str(shot_id or "").strip() and isinstance(row, dict) and str(shot_id).strip() in normalized_planned_shot_ids
    }
    valid_shot_ids = list(normalized_edit_data.keys())
    chorus_shots = [shot_id for shot_id, row in normalized_edit_data.items() if str(row.get("section_emphasis", "")).strip() == "chorus_push"]
    verse_shots = [shot_id for shot_id, row in normalized_edit_data.items() if str(row.get("section_emphasis", "")).strip() == "sequence_support"]
    all_shots = valid_shot_ids

    chorus_mode_scores = [
        _float(_render_planning_row(render_planning, shot_id).get("mode_importance_score"), 0.0)
        for shot_id in chorus_shots
    ]
    chorus_performance_material_ratio = _avg(chorus_mode_scores)
    chorus_frontality_advantage = _avg([1.0 if score >= 1.0 else 0.0 for score in chorus_mode_scores])

    chorus_count = _avg([_float(render_counts.get(shot_id), 0.0) for shot_id in chorus_shots])
    verse_count = _avg([_float(render_counts.get(shot_id), 0.0) for shot_id in verse_shots])
    chorus_cut_density_advantage = max(0.0, min(1.0, (chorus_count - verse_count) / 2.0))

    chorus_priority = _avg([_float(render_priorities.get(shot_id), 0.0) for shot_id in chorus_shots])
    verse_priority = _avg([_float(render_priorities.get(shot_id), 0.0) for shot_id in verse_shots])
    chorus_motion_energy_advantage = max(0.0, min(1.0, chorus_priority - verse_priority))
    chorus_highlight_selection_advantage = _avg([1.0 if _float(render_priorities.get(shot_id), 0.0) >= 0.8 else 0.0 for shot_id in chorus_shots])

    chorus_emphasis_score = round(
        (0.30 * chorus_performance_material_ratio)
        + (0.20 * chorus_cut_density_advantage)
        + (0.20 * chorus_frontality_advantage)
        + (0.15 * chorus_motion_energy_advantage)
        + (0.15 * chorus_highlight_selection_advantage),
        2,
    )

    unique_emphases = {
        str(row.get("section_emphasis", "")).strip()
        for row in normalized_edit_data.values()
        if str(row.get("section_emphasis", "")).strip()
    }
    repetition_penalty_mean = max(0.0, 1.0 - (_safe_divide(len(unique_emphases), len(all_shots)) if all_shots else 0.0))
    transition_intentionality_score = round(
        _safe_divide(
            sum(
                1
                for row in normalized_edit_data.values()
                if (
                    str(row.get("transition_in", "")).strip() not in {"", "cut_in"}
                    or str(row.get("transition_out", "")).strip() not in {"", "cut_out"}
                )
            ),
            len(all_shots),
        ),
        2,
    )
    transition_flatness_score = max(0.0, 1.0 - transition_intentionality_score)
    section_variation_deficit = max(0.0, 1.0 - min(1.0, _safe_divide(len(unique_emphases), 3.0)))
    motion_energy_deficit = max(0.0, 1.0 - _avg([_float(render_priorities.get(shot_id), 0.0) for shot_id in valid_shot_ids]))
    slideshow_risk_score = round(
        (0.35 * repetition_penalty_mean)
        + (0.25 * transition_flatness_score)
        + (0.20 * section_variation_deficit)
        + (0.20 * motion_energy_deficit),
        2,
    )

    return {
        "chorus_emphasis_score": chorus_emphasis_score,
        "slideshow_risk_score": slideshow_risk_score,
        "transition_intentionality_score": transition_intentionality_score,
        "chorus_emphasis_within_threshold": chorus_emphasis_score >= 0.62,
        "slideshow_risk_within_threshold": slideshow_risk_score <= 0.38,
    }



def build_review_report(
    *,
    planned_shot_ids: list[str],
    still_results: list[dict],
    clip_results: list[dict],
    still_status: dict[str, bool],
    clip_status: dict[str, bool],
    final_video_exists: bool,
    rerender_targets: list[str],
    rerender_reasons: dict[str, list[str]],
    audio_video_drift_sec: float,
    config: dict,
    shot_plan: list[dict] | None = None,
    render_plan: list[dict] | None = None,
    music_file: str = "",
    final_video_path: str = "",
    edit_intent_by_shot: dict[str, dict] | None = None,
    render_count_by_shot: dict[str, int] | None = None,
    render_priority_by_shot: dict[str, float] | None = None,
    render_planning_by_shot: dict[str, dict] | None = None,
    assembly_quality_summary: dict[str, object] | None = None,
) -> dict:
    signals = build_quality_signals(
        planned_shot_ids=planned_shot_ids,
        still_status=still_status,
        clip_status=clip_status,
        final_video_exists=final_video_exists,
        audio_video_drift_sec=audio_video_drift_sec,
        config=config,
        rerender_reasons=rerender_reasons,
    )
    blocking_checks = signals["blocking_checks"]
    non_blocking_checks = signals["non_blocking_checks"]
    still_done = int(signals["still_done"])
    clip_done = int(signals["clip_done"])
    priority_scores = {shot_id: rerender_priority_score(reasons) for shot_id, reasons in rerender_reasons.items()}
    shot_scores = build_shot_quality_scores(
        planned_shot_ids=planned_shot_ids,
        still_status=still_status,
        clip_status=clip_status,
        rerender_reasons=rerender_reasons,
    )
    benchmark_dimensions = summarize_benchmark_dimensions(rerender_reasons)
    review_signal_buckets = summarize_review_signal_buckets(
        blocking_checks=blocking_checks,
        non_blocking_checks=non_blocking_checks,
    )
    computed_assembly_quality_summary = summarize_assembly_quality(
        planned_shot_ids=planned_shot_ids,
        edit_intent_by_shot=edit_intent_by_shot,
        render_count_by_shot=render_count_by_shot,
        render_priority_by_shot=render_priority_by_shot,
        render_planning_by_shot=render_planning_by_shot,
    )
    has_assembly_metadata = (
        isinstance(edit_intent_by_shot, dict)
        and bool(edit_intent_by_shot)
        and isinstance(render_count_by_shot, dict)
        and bool(render_count_by_shot)
        and isinstance(render_priority_by_shot, dict)
        and bool(render_priority_by_shot)
        and isinstance(render_planning_by_shot, dict)
        and bool(render_planning_by_shot)
    )
    effective_assembly_quality_summary = (
        assembly_quality_summary
        if isinstance(assembly_quality_summary, dict)
        else (computed_assembly_quality_summary if has_assembly_metadata else None)
    )
    publishability_summary = summarize_publishability(
        blocking_checks=blocking_checks,
        non_blocking_checks=non_blocking_checks,
        rerender_reasons=rerender_reasons,
        assembly_quality_summary=effective_assembly_quality_summary,
    )
    rerender_plan = build_rerender_plan(
        rerender_targets=rerender_targets,
        rerender_reasons=rerender_reasons,
    )
    rerender_payload = build_rerender_payload(rerender_plan)
    rerender_execution_payloads = build_rerender_execution_payloads(
        rerender_payload=rerender_payload,
        shot_plan=shot_plan or [],
        render_plan=render_plan or [],
        still_results=still_results,
        music_file=music_file,
        final_video_path=final_video_path,
    )
    edit_intent_summary = summarize_edit_intent(edit_intent_by_shot)
    mv_intent_checks = build_mv_intent_checks(edit_intent_summary)
    assembly_quality_summary = effective_assembly_quality_summary
    return {
        "status": "done" if all(blocking_checks.values()) and not rerender_targets else "needs_rerender",
        "audio_video_drift_sec": audio_video_drift_sec,
        "planned_counts": {
            "shots": len(planned_shot_ids),
            "stills": len(still_results),
            "clips": len(clip_results),
        },
        "completed_counts": {
            "stills": still_done,
            "clips": clip_done,
        },
        "coverage": signals["coverage"],
        "severity": signals["severity"],
        "scores": {
            "overall": signals["scores"]["overall"],
            "shots": shot_scores,
        },
        "blocking_checks": blocking_checks,
        "non_blocking_checks": non_blocking_checks,
        "rerender_targets": rerender_targets,
        "rerender_reasons": rerender_reasons,
        "rerender_priority_scores": priority_scores,
        "rerender_plan": rerender_plan,
        "rerender_payload": rerender_payload,
        "rerender_execution_payloads": rerender_execution_payloads,
        "benchmark_dimensions": benchmark_dimensions,
        "review_signal_buckets": review_signal_buckets,
        "publishability_summary": publishability_summary,
        "edit_intent_summary": edit_intent_summary,
        "mv_intent_checks": mv_intent_checks,
        "assembly_quality_summary": assembly_quality_summary,
    }



def _avg(values: list[float]) -> float:
    cleaned = [float(value) for value in values if value is not None]
    return round(sum(cleaned) / len(cleaned), 3) if cleaned else 0.0



def _safe_divide(numerator: float, denominator: float) -> float:
    try:
        denominator_value = float(denominator)
    except Exception:
        return 0.0
    if denominator_value == 0.0:
        return 0.0
    return float(numerator) / denominator_value



def _float(value: object, default: float) -> float:
    try:
        parsed = float(value)
    except Exception:
        return default
    return parsed if math.isfinite(parsed) else default



def _render_planning_row(render_planning: dict[str, dict], shot_id: str) -> dict:
    row = render_planning.get(shot_id)
    return dict(row) if isinstance(row, dict) else {}
