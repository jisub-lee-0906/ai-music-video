from __future__ import annotations


def rerender_targets(
    planned_shot_ids: list[str],
    still_status: dict[str, bool],
    clip_status: dict[str, bool],
    config: dict,
    *,
    final_video_exists: bool = True,
    audio_video_drift_sec: float = 0.0,
    coverage: dict[str, float] | None = None,
    shot_scores: dict[str, float] | None = None,
    quality_findings: dict[str, list[str]] | None = None,
) -> list[str]:
    reasons = rerender_reasons(
        planned_shot_ids,
        still_status,
        clip_status,
        final_video_exists=final_video_exists,
        audio_video_drift_sec=audio_video_drift_sec,
        coverage=coverage,
        config=config,
        quality_findings=quality_findings,
    )
    scored = sorted(
        reasons.items(),
        key=lambda item: (
            float(shot_scores.get(item[0], 100.0)) if isinstance(shot_scores, dict) else 100.0,
            -rerender_priority_score(item[1]),
            item[0],
        ),
    )
    targets = [shot_id for shot_id, _reasons in scored]
    review = config.get("review", {}) if isinstance(config, dict) else {}
    try:
        limit = int(review.get("max_rerender_targets", 0) or 0)
    except Exception:
        limit = 0
    return targets if limit <= 0 else targets[:limit]



def rerender_reasons(
    planned_shot_ids: list[str],
    still_status: dict[str, bool],
    clip_status: dict[str, bool],
    *,
    final_video_exists: bool = True,
    audio_video_drift_sec: float = 0.0,
    coverage: dict[str, float] | None = None,
    config: dict | None = None,
    quality_findings: dict[str, list[str]] | None = None,
) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    review = config.get("review", {}) if isinstance(config, dict) else {}
    try:
        max_drift = float(review.get("max_audio_video_drift_sec", 0.5) or 0.5)
    except Exception:
        max_drift = 0.5
    try:
        min_stills = float(review.get("min_stills_coverage_ratio", 0.8) or 0.8)
    except Exception:
        min_stills = 0.8
    try:
        min_clips = float(review.get("min_clips_coverage_ratio", 0.8) or 0.8)
    except Exception:
        min_clips = 0.8

    coverage = coverage or {"stills_ratio": 1.0, "clips_ratio": 1.0}
    quality_failures: list[str] = []
    if not final_video_exists:
        quality_failures.append("missing_final_video")
    if audio_video_drift_sec > max_drift:
        quality_failures.append("drift_too_high")
    if float(coverage.get("stills_ratio", 1.0)) < min_stills or float(coverage.get("clips_ratio", 1.0)) < min_clips:
        quality_failures.append("coverage_too_low")

    findings_map = quality_findings if isinstance(quality_findings, dict) else {}
    for shot_id in planned_shot_ids:
        reasons: list[str] = []
        if not still_status.get(shot_id, False):
            reasons.append("missing_still")
        if not clip_status.get(shot_id, False):
            reasons.append("missing_clip")
        reasons.extend(x for x in quality_failures if x not in reasons)
        reasons.extend(_normalize_quality_findings(findings_map.get(shot_id, []), reasons))
        if reasons:
            out[shot_id] = reasons
    return out


def _normalize_quality_findings(findings: list[str] | tuple[str, ...] | set[str], existing: list[str]) -> list[str]:
    out: list[str] = []
    for finding in findings if isinstance(findings, (list, tuple, set)) else []:
        value = str(finding or "").strip()
        if not value or value in existing or value in out:
            continue
        out.append(value)
    return out



def rerender_priority_score(reasons: list[str]) -> int:
    weights = {
        "missing_final_video": 6,
        "drift_too_high": 4,
        "coverage_too_low": 3,
        "missing_clip": 3,
        "missing_still": 2,
        "terminal_frame_corruption": 6,
        "continuity_break": 5,
        "duplicate_subject": 5,
        "layered_overlay_intrusion": 5,
        "identity_drift": 4,
    }
    return sum(int(weights.get(reason, 1)) for reason in reasons)
