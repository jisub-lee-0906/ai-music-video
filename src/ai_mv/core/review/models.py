from __future__ import annotations

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
    publishability_summary = summarize_publishability(
        blocking_checks=blocking_checks,
        non_blocking_checks=non_blocking_checks,
        rerender_reasons=rerender_reasons,
    )
    rerender_plan = build_rerender_plan(
        rerender_targets=rerender_targets,
        rerender_reasons=rerender_reasons,
    )
    rerender_payload = build_rerender_payload(rerender_plan)
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
        "benchmark_dimensions": benchmark_dimensions,
        "review_signal_buckets": review_signal_buckets,
        "publishability_summary": publishability_summary,
    }
