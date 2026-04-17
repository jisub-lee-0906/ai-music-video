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

_GUIDANCE_BY_CHECK = {
    "final_video_exists": "assemble final mv output before subjective quality review",
    "all_stills_rendered": "rerender missing stills before clip review",
    "stills_coverage_within_threshold": "increase still coverage until every planned shot has a usable keyframe",
    "all_clips_rendered": "rerender missing clips before final assembly",
    "clips_coverage_within_threshold": "increase clip coverage until every planned shot has a usable motion segment",
    "audio_video_sync_within_tolerance": "repair audio-video timing drift before publishability review",
    "terminal_frames_clean": "rerender affected clips with cleaner terminal frames and shorter motion range",
    "duplicate_subject_absent": "tighten single-subject framing and remove duplicate subject artifacts",
    "style_identity": "strengthen style-identity prompt constraints and rerender weakest shots",
    "visual_continuity_preserved": "rerender continuity-break shots and preserve identity across adjacent shots",
    "mood_consistency": "rerender mood-drift shots to match the song section and neighboring shots",
}

_TECHNICAL_PRIORITY = (
    ("final_video_exists", "assemble_or_reassemble_final_video"),
    ("audio_video_sync_within_tolerance", "repair_audio_video_sync"),
    ("all_stills_rendered", "rerender_missing_stills"),
    ("stills_coverage_within_threshold", "rerender_missing_stills"),
    ("all_clips_rendered", "rerender_missing_clips"),
    ("clips_coverage_within_threshold", "rerender_missing_clips"),
)

_ISOLATED_PRIORITY = (
    ("terminal_frames_clean", "rerender_clips_with_terminal_frame_cleanup"),
    ("duplicate_subject_absent", "rerender_weak_shots_with_prompt_tightening"),
    ("style_identity", "rerender_weak_shots_with_prompt_tightening"),
)

_FINAL_PRIORITY = (
    ("visual_continuity_preserved", "rerender_continuity_break_shots"),
    ("mood_consistency", "rerender_mood_drift_shots"),
)

_BUCKET_REASON_CODES = {
    "technical_completion": {
        "missing_final_video",
        "drift_too_high",
        "coverage_too_low",
        "missing_still",
        "missing_clip",
    },
    "isolated_asset_quality": {
        "terminal_frame_corruption",
        "duplicate_subject",
        "identity_drift",
    },
    "final_mv_publishability": {
        "continuity_break",
        "identity_drift",
    },
}


def summarize_publishability(
    *,
    blocking_checks: dict[str, bool],
    non_blocking_checks: dict[str, bool],
    rerender_reasons: dict[str, list[str]] | None = None,
) -> dict[str, dict[str, object]]:
    blocking = blocking_checks if isinstance(blocking_checks, dict) else {}
    non_blocking = non_blocking_checks if isinstance(non_blocking_checks, dict) else {}
    reasons_map = rerender_reasons if isinstance(rerender_reasons, dict) else {}
    return {
        "technical_completion": _summary(
            "technical_completion",
            _TECHNICAL_COMPLETION_CHECKS,
            blocking,
            non_blocking,
            reasons_map,
            field_name="blocking_failures",
            action_priority=_TECHNICAL_PRIORITY,
        ),
        "isolated_asset_quality": _summary(
            "isolated_asset_quality",
            _ISOLATED_ASSET_QUALITY_CHECKS,
            blocking,
            non_blocking,
            reasons_map,
            action_priority=_ISOLATED_PRIORITY,
        ),
        "final_mv_publishability": _summary(
            "final_mv_publishability",
            _FINAL_MV_PUBLISHABILITY_CHECKS,
            blocking,
            non_blocking,
            reasons_map,
            action_priority=_FINAL_PRIORITY,
        ),
    }



def _summary(
    bucket_name: str,
    check_names: tuple[str, ...],
    blocking_checks: dict[str, bool],
    non_blocking_checks: dict[str, bool],
    rerender_reasons: dict[str, list[str]],
    *,
    field_name: str = "failed_checks",
    action_priority: tuple[tuple[str, str], ...] = (),
) -> dict[str, object]:
    failures: list[str] = []
    for check_name in check_names:
        value = _lookup_check(check_name, blocking_checks, non_blocking_checks)
        if value is False:
            failures.append(check_name)
    next_action = _next_action(failures, action_priority)
    return {
        "passed": not failures,
        field_name: failures,
        "next_action": next_action,
        "rerender_guidance": [_GUIDANCE_BY_CHECK[check_name] for check_name in failures if check_name in _GUIDANCE_BY_CHECK],
        "rerender_bundle": _rerender_bundle(bucket_name, next_action, rerender_reasons),
    }



def _next_action(failures: list[str], action_priority: tuple[tuple[str, str], ...]) -> str:
    if not failures:
        return "no_action"
    for check_name, action_name in action_priority:
        if check_name in failures:
            return action_name
    return "review_failed_checks"



def _rerender_bundle(bucket_name: str, action_name: str, rerender_reasons: dict[str, list[str]]) -> dict[str, object]:
    if action_name == "no_action":
        return {
            "action": "no_action",
            "target_shots": [],
            "reason_codes": [],
        }
    bucket_reason_codes = _BUCKET_REASON_CODES.get(bucket_name, set())
    target_shots: list[str] = []
    reason_codes: set[str] = set()
    for shot_id, reasons in rerender_reasons.items():
        matched_reasons = [reason for reason in reasons if reason in bucket_reason_codes] if isinstance(reasons, list) else []
        if not matched_reasons:
            continue
        normalized_shot_id = str(shot_id or "").strip()
        if normalized_shot_id:
            target_shots.append(normalized_shot_id)
        reason_codes.update(str(reason).strip() for reason in matched_reasons if str(reason).strip())
    return {
        "action": action_name,
        "target_shots": target_shots,
        "reason_codes": sorted(reason_codes),
    }



def _lookup_check(check_name: str, blocking_checks: dict[str, bool], non_blocking_checks: dict[str, bool]) -> bool | None:
    if check_name in blocking_checks:
        return bool(blocking_checks[check_name])
    if check_name in non_blocking_checks:
        return bool(non_blocking_checks[check_name])
    return None
