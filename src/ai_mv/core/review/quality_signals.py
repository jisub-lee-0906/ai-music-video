from __future__ import annotations


def build_quality_signals(
    *,
    planned_shot_ids: list[str],
    still_status: dict[str, bool],
    clip_status: dict[str, bool],
    final_video_exists: bool,
    audio_video_drift_sec: float,
    config: dict,
) -> dict:
    total = len(planned_shot_ids)
    still_done = sum(1 for shot_id in planned_shot_ids if still_status.get(shot_id, False))
    clip_done = sum(1 for shot_id in planned_shot_ids if clip_status.get(shot_id, False))
    coverage = {
        "stills_ratio": round((still_done / total), 3) if total else 0.0,
        "clips_ratio": round((clip_done / total), 3) if total else 0.0,
    }
    review_cfg = config.get("review", {}) if isinstance(config, dict) else {}
    try:
        max_drift = float(review_cfg.get("max_audio_video_drift_sec", 0.5) or 0.5)
    except Exception:
        max_drift = 0.5
    try:
        min_stills = float(review_cfg.get("min_stills_coverage_ratio", 0.8) or 0.8)
    except Exception:
        min_stills = 0.8
    try:
        min_clips = float(review_cfg.get("min_clips_coverage_ratio", 0.8) or 0.8)
    except Exception:
        min_clips = 0.8
    try:
        min_overall_score = float(review_cfg.get("min_overall_score", 0.0) or 0.0)
    except Exception:
        min_overall_score = 0.0

    drift_severity = "low"
    if audio_video_drift_sec > max_drift * 1.5:
        drift_severity = "high"
    elif audio_video_drift_sec > max_drift:
        drift_severity = "medium"

    lowest_coverage = min(float(coverage.get("stills_ratio", 0.0)), float(coverage.get("clips_ratio", 0.0)))
    min_required_coverage = min(min_stills, min_clips)
    coverage_severity = "low"
    if lowest_coverage < max(0.0, min_required_coverage - 0.4):
        coverage_severity = "high"
    elif lowest_coverage < min_required_coverage:
        coverage_severity = "medium"

    style_identity = final_video_exists and clip_done > 0
    style_constraints_respected = final_video_exists

    non_blocking_checks = {
        "camera_restraint": final_video_exists,
        "memorable_shot": clip_done > 0,
        "style_identity": style_identity,
        "citypop_identity": style_identity,
        "mood_consistency": final_video_exists and still_done > 0,
    }

    overall_score = 100.0
    if not final_video_exists:
        overall_score -= 35.0
    if drift_severity == "medium":
        overall_score -= 15.0
    elif drift_severity == "high":
        overall_score -= 30.0
    if coverage_severity == "medium":
        overall_score -= 15.0
    elif coverage_severity == "high":
        overall_score -= 30.0
    if not non_blocking_checks["memorable_shot"]:
        overall_score -= 5.0
    if not non_blocking_checks["mood_consistency"]:
        overall_score -= 5.0
    overall_score = round(max(0.0, min(100.0, overall_score)), 2)

    blocking_checks = {
        "final_video_exists": final_video_exists,
        "all_stills_rendered": still_done == total and bool(planned_shot_ids),
        "all_clips_rendered": clip_done == total and bool(planned_shot_ids),
        "audio_video_sync_within_tolerance": audio_video_drift_sec <= max_drift,
        "stills_coverage_within_threshold": coverage["stills_ratio"] >= min_stills,
        "clips_coverage_within_threshold": coverage["clips_ratio"] >= min_clips,
        "overall_score_within_threshold": overall_score >= min_overall_score,
        "style_constraints_respected": style_constraints_respected,
        "not_kpop_or_cyberpunk": style_constraints_respected,
    }
    return {
        "still_done": still_done,
        "clip_done": clip_done,
        "coverage": coverage,
        "severity": {
            "drift": drift_severity,
            "coverage": coverage_severity,
        },
        "scores": {
            "overall": overall_score,
        },
        "blocking_checks": blocking_checks,
        "non_blocking_checks": non_blocking_checks,
    }
