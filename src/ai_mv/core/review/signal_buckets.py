from __future__ import annotations

_MEASURABLE_DETERMINISTIC_CHECKS = (
    "final_video_exists",
    "all_stills_rendered",
    "all_clips_rendered",
    "audio_video_sync_within_tolerance",
    "stills_coverage_within_threshold",
    "clips_coverage_within_threshold",
    "overall_score_within_threshold",
)

_HEURISTIC_PROXY_CHECKS = (
    "terminal_frames_clean",
    "visual_continuity_preserved",
    "duplicate_subject_absent",
    "overlay_intrusion_absent",
    "subject_match_preserved",
    "environment_match_preserved",
    "motion_source_safe",
    "scene_intrusion_absent",
    "panel_layout_absent",
    "collage_layout_absent",
    "split_screen_absent",
    "camera_restraint",
    "memorable_shot",
)

_MODEL_JUDGED_CHECKS = (
    "style_identity",
    "mood_consistency",
)


def summarize_review_signal_buckets(*, blocking_checks: dict[str, bool], non_blocking_checks: dict[str, bool]) -> dict[str, dict[str, object]]:
    blocking = blocking_checks if isinstance(blocking_checks, dict) else {}
    non_blocking = non_blocking_checks if isinstance(non_blocking_checks, dict) else {}
    return {
        "measurable_deterministic": _bucket(_MEASURABLE_DETERMINISTIC_CHECKS, blocking, non_blocking),
        "heuristic_proxy": _bucket(_HEURISTIC_PROXY_CHECKS, blocking, non_blocking),
        "model_judged": _bucket(_MODEL_JUDGED_CHECKS, blocking, non_blocking),
    }



def _bucket(check_names: tuple[str, ...], blocking_checks: dict[str, bool], non_blocking_checks: dict[str, bool]) -> dict[str, object]:
    failed_checks: list[str] = []
    for check_name in check_names:
        value = _lookup_check(check_name, blocking_checks, non_blocking_checks)
        if value is False:
            failed_checks.append(check_name)
    return {
        "passed": not failed_checks,
        "failed_checks": failed_checks,
    }



def _lookup_check(check_name: str, blocking_checks: dict[str, bool], non_blocking_checks: dict[str, bool]) -> bool | None:
    if check_name in blocking_checks:
        return bool(blocking_checks[check_name])
    if check_name in non_blocking_checks:
        return bool(non_blocking_checks[check_name])
    return None
