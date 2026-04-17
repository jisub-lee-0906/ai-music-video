from __future__ import annotations


_TECHNICAL_COMPLETION_CHECKS = (
    "final_video_exists",
    "all_stills_rendered",
    "all_clips_rendered",
    "audio_video_sync_within_tolerance",
    "stills_coverage_within_threshold",
    "clips_coverage_within_threshold",
)

_ISOLATED_ASSET_QUALITY_CHECKS = (
    "terminal_frames_clean",
    "duplicate_subject_absent",
    "style_identity",
)

_FINAL_MV_PUBLISHABILITY_CHECKS = (
    "visual_continuity_preserved",
    "mood_consistency",
)


def summarize_publishability(*, blocking_checks: dict[str, bool], non_blocking_checks: dict[str, bool]) -> dict[str, dict[str, object]]:
    blocking = blocking_checks if isinstance(blocking_checks, dict) else {}
    non_blocking = non_blocking_checks if isinstance(non_blocking_checks, dict) else {}
    return {
        "technical_completion": _summary(_TECHNICAL_COMPLETION_CHECKS, blocking, non_blocking, field_name="blocking_failures"),
        "isolated_asset_quality": _summary(_ISOLATED_ASSET_QUALITY_CHECKS, blocking, non_blocking),
        "final_mv_publishability": _summary(_FINAL_MV_PUBLISHABILITY_CHECKS, blocking, non_blocking),
    }



def _summary(
    check_names: tuple[str, ...],
    blocking_checks: dict[str, bool],
    non_blocking_checks: dict[str, bool],
    *,
    field_name: str = "failed_checks",
) -> dict[str, object]:
    failures: list[str] = []
    for check_name in check_names:
        value = _lookup_check(check_name, blocking_checks, non_blocking_checks)
        if value is False:
            failures.append(check_name)
    return {
        "passed": not failures,
        field_name: failures,
    }



def _lookup_check(check_name: str, blocking_checks: dict[str, bool], non_blocking_checks: dict[str, bool]) -> bool | None:
    if check_name in blocking_checks:
        return bool(blocking_checks[check_name])
    if check_name in non_blocking_checks:
        return bool(non_blocking_checks[check_name])
    return None
