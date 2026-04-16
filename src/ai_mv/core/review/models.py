from __future__ import annotations

from ai_mv.core.review.quality_signals import build_quality_signals
from ai_mv.core.review.rerender_policy import rerender_priority_score



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
    }
