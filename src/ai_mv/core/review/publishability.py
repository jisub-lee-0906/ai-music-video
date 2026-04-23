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
    "subject_match_preserved",
    "environment_match_preserved",
    "scene_intrusion_absent",
    "panel_layout_absent",
    "collage_layout_absent",
    "split_screen_absent",
)

_FINAL_MV_PUBLISHABILITY_CHECKS = (
    "visual_continuity_preserved",
    "mood_consistency",
    "motion_source_safe",
    "chorus_emphasis_within_threshold",
    "slideshow_risk_within_threshold",
    "safe_editing_within_threshold",
    "character_payoff_present",
    "background_dominance_within_threshold",
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
    "subject_match_preserved": "rerender weak-subject-match shots with tighter protagonist constraints",
    "environment_match_preserved": "rerender weak-environment-match shots with stronger world and location anchors",
    "scene_intrusion_absent": "rerender scene-intrusion shots and remove unrelated scene content",
    "panel_layout_absent": "rerender panelized keyframes as single-frame cinematic stills",
    "collage_layout_absent": "rerender collage-like keyframes as single uninterrupted compositions",
    "split_screen_absent": "rerender split-screen keyframes as one continuous shot",
    "visual_continuity_preserved": "rerender continuity-break shots and preserve identity across adjacent shots",
    "mood_consistency": "rerender mood-drift shots to match the song section and neighboring shots",
    "motion_source_safe": "rerender motion-fragile shots with safer keyframes and simpler motion sources",
    "chorus_emphasis_within_threshold": "revise assembly weights so chorus reads stronger than verse before clip rerender",
    "slideshow_risk_within_threshold": "revise transition selection and clip ordering before rerendering clips",
    "safe_editing_within_threshold": "revise assembly pattern selection and cut density to avoid repetitive safe edits before rerendering clips",
    "character_payoff_present": "rerender weak-payoff shots so the character reads as the emotional center instead of background mood",
    "background_dominance_within_threshold": "rerender background-dominant shots with stronger subject scale and foreground payoff",
}

_TECHNICAL_PRIORITY = (
    ("final_video_exists", "assemble_or_reassemble_final_video"),
    ("all_stills_rendered", "rerender_missing_stills"),
    ("stills_coverage_within_threshold", "rerender_missing_stills"),
    ("all_clips_rendered", "rerender_missing_clips"),
    ("clips_coverage_within_threshold", "rerender_missing_clips"),
    ("audio_video_sync_within_tolerance", "repair_audio_video_sync"),
)

_ISOLATED_PRIORITY = (
    ("terminal_frames_clean", "rerender_clips_with_terminal_frame_cleanup"),
    ("duplicate_subject_absent", "rerender_weak_shots_with_prompt_tightening"),
    ("scene_intrusion_absent", "rerender_scene_intrusion_shots"),
    ("panel_layout_absent", "rerender_panelized_keyframes"),
    ("collage_layout_absent", "rerender_panelized_keyframes"),
    ("split_screen_absent", "rerender_panelized_keyframes"),
    ("subject_match_preserved", "rerender_weak_shots_with_prompt_tightening"),
    ("environment_match_preserved", "rerender_weak_shots_with_prompt_tightening"),
    ("style_identity", "rerender_weak_shots_with_prompt_tightening"),
)

_FINAL_PRIORITY = (
    ("chorus_emphasis_within_threshold", "revise_assembly_weights_before_clip_rerender"),
    ("slideshow_risk_within_threshold", "revise_transition_selection"),
    ("safe_editing_within_threshold", "revise_transition_selection"),
    ("character_payoff_present", "rerender_character_payoff_shots"),
    ("background_dominance_within_threshold", "rerender_character_payoff_shots"),
    ("visual_continuity_preserved", "rerender_continuity_break_shots"),
    ("motion_source_safe", "rerender_motion_fragile_shots_with_safer_keyframes"),
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
        "weak_subject_match",
        "weak_environment_match",
        "unrelated_scene_intrusion",
        "panel_layout",
        "collage_layout",
        "split_screen",
    },
    "final_mv_publishability": {
        "continuity_break",
        "identity_drift",
        "motion_fragile_frame",
        "chorus_not_stronger_than_verse",
        "arbitrary_transitions",
        "weak_character_payoff",
        "background_dominant_composition",
    },
}


def summarize_publishability(
    *,
    blocking_checks: dict[str, bool],
    non_blocking_checks: dict[str, bool],
    rerender_reasons: dict[str, list[str]] | None = None,
    assembly_quality_summary: dict[str, object] | None = None,
    shot_plan: list[dict] | None = None,
    material_plan: list[dict] | None = None,
    render_plan: list[dict] | None = None,
    still_results: list[dict] | None = None,
    clip_results: list[dict] | None = None,
) -> dict[str, dict[str, object]]:
    blocking = blocking_checks if isinstance(blocking_checks, dict) else {}
    non_blocking = non_blocking_checks if isinstance(non_blocking_checks, dict) else {}
    reasons_map = rerender_reasons if isinstance(rerender_reasons, dict) else {}
    assembly = assembly_quality_summary if isinstance(assembly_quality_summary, dict) else {}
    rerender_context_by_shot = _build_rerender_context_by_shot(
        shot_plan=shot_plan or [],
        material_plan=material_plan or [],
        render_plan=render_plan or [],
        still_results=still_results or [],
        clip_results=clip_results or [],
    )
    return {
        "technical_completion": _summary(
            "technical_completion",
            _TECHNICAL_COMPLETION_CHECKS,
            blocking,
            non_blocking,
            reasons_map,
            field_name="blocking_failures",
            action_priority=_TECHNICAL_PRIORITY,
            rerender_context_by_shot=rerender_context_by_shot,
        ),
        "isolated_asset_quality": _summary(
            "isolated_asset_quality",
            _ISOLATED_ASSET_QUALITY_CHECKS,
            blocking,
            non_blocking,
            reasons_map,
            action_priority=_ISOLATED_PRIORITY,
            rerender_context_by_shot=rerender_context_by_shot,
        ),
        "final_mv_publishability": _summary(
            "final_mv_publishability",
            _FINAL_MV_PUBLISHABILITY_CHECKS,
            blocking,
            non_blocking,
            reasons_map,
            action_priority=_FINAL_PRIORITY,
            assembly_quality_summary=assembly,
            rerender_context_by_shot=rerender_context_by_shot,
        ),
    }



def build_final_review_summary(
    *,
    blocking_checks: dict[str, bool],
    non_blocking_checks: dict[str, bool],
    publishability_summary: dict[str, dict[str, object]],
    overall_score: float,
    assembly_quality_summary: dict[str, object] | None = None,
) -> dict[str, object]:
    blocking = blocking_checks if isinstance(blocking_checks, dict) else {}
    non_blocking = non_blocking_checks if isinstance(non_blocking_checks, dict) else {}
    summary = publishability_summary if isinstance(publishability_summary, dict) else {}
    assembly = assembly_quality_summary if isinstance(assembly_quality_summary, dict) else {}

    technical_completion_score = _check_group_score(_TECHNICAL_COMPLETION_CHECKS, blocking, non_blocking, None)
    material_quality_score = _check_group_score(_ISOLATED_ASSET_QUALITY_CHECKS, blocking, non_blocking, None)
    final_mv_quality_score = _final_mv_quality_score(blocking, non_blocking, assembly, technical_completion_score)
    publishability_tier = _publishability_tier(blocking, non_blocking, final_mv_quality_score)
    recommended_next_action = _recommended_next_action(summary, publishability_tier)

    return {
        "overall_status": "pass" if publishability_tier == "publishable" else "review_required",
        "publishability_tier": publishability_tier,
        "recommended_next_action": recommended_next_action,
        "scores": {
            "overall": round(float(overall_score), 2),
            "technical_completion": technical_completion_score,
            "material_quality": material_quality_score,
            "final_mv_quality": final_mv_quality_score,
        },
    }



def classify_rerender_target(reason_codes: list[str]) -> dict[str, object]:
    normalized_reasons = [str(reason).strip() for reason in reason_codes if str(reason).strip()]
    normalized_reason_set = {reason for reason in normalized_reasons if reason}
    if {"continuity_break", "identity_drift"}.issubset(normalized_reason_set):
        return {
            "bucket": "final_mv_publishability",
            "recommended_action": "rerender_continuity_break_shots",
            "rerender_prescription": _rerender_prescription("rerender_continuity_break_shots", normalized_reasons),
        }
    if "weak_character_payoff" in normalized_reason_set or "background_dominant_composition" in normalized_reason_set:
        return {
            "bucket": "final_mv_publishability",
            "recommended_action": "rerender_character_payoff_shots",
            "rerender_prescription": _rerender_prescription("rerender_character_payoff_shots", normalized_reasons),
        }
    if "chorus_not_stronger_than_verse" in normalized_reason_set:
        return {
            "bucket": "final_mv_publishability",
            "recommended_action": "revise_assembly_weights_before_clip_rerender",
            "rerender_prescription": _rerender_prescription("revise_assembly_weights_before_clip_rerender", normalized_reasons),
        }
    if "arbitrary_transitions" in normalized_reason_set:
        return {
            "bucket": "final_mv_publishability",
            "recommended_action": "revise_transition_selection",
            "rerender_prescription": _rerender_prescription("revise_transition_selection", normalized_reasons),
        }
    for bucket_name, reason_to_action in (
        (
            "technical_completion",
            {
                "missing_final_video": "assemble_or_reassemble_final_video",
                "coverage_too_low": "rerender_missing_stills",
                "missing_still": "rerender_missing_stills",
                "missing_clip": "rerender_missing_clips",
                "drift_too_high": "repair_audio_video_sync",
            },
        ),
        (
            "isolated_asset_quality",
            {
                "terminal_frame_corruption": "rerender_clips_with_terminal_frame_cleanup",
                "duplicate_subject": "rerender_weak_shots_with_prompt_tightening",
                "unrelated_scene_intrusion": "rerender_scene_intrusion_shots",
                "panel_layout": "rerender_panelized_keyframes",
                "collage_layout": "rerender_panelized_keyframes",
                "split_screen": "rerender_panelized_keyframes",
                "weak_subject_match": "rerender_weak_shots_with_prompt_tightening",
                "weak_environment_match": "rerender_weak_shots_with_prompt_tightening",
                "identity_drift": "rerender_weak_shots_with_prompt_tightening",
            },
        ),
        (
            "final_mv_publishability",
            {
                "continuity_break": "rerender_continuity_break_shots",
                "motion_fragile_frame": "rerender_motion_fragile_shots_with_safer_keyframes",
                "identity_drift": "rerender_continuity_break_shots",
            },
        ),
    ):
        for reason, action_name in reason_to_action.items():
            if reason in normalized_reasons:
                return {
                    "bucket": bucket_name,
                    "recommended_action": action_name,
                    "rerender_prescription": _rerender_prescription(action_name, normalized_reasons),
                }
    return {
        "bucket": "unclassified",
        "recommended_action": "review_failed_checks",
        "rerender_prescription": _rerender_prescription("review_failed_checks", normalized_reasons),
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
    assembly_quality_summary: dict[str, object] | None = None,
    rerender_context_by_shot: dict[str, dict[str, str]] | None = None,
) -> dict[str, object]:
    failures: list[str] = []
    assembly = assembly_quality_summary if isinstance(assembly_quality_summary, dict) else None
    for check_name in check_names:
        if assembly is not None and check_name in assembly:
            value = bool(assembly.get(check_name))
        else:
            value = _lookup_check(check_name, blocking_checks, non_blocking_checks)
        if value is False:
            failures.append(check_name)
    next_action = _next_action(failures, action_priority)
    return {
        "passed": not failures,
        field_name: failures,
        "next_action": next_action,
        "rerender_guidance": [_GUIDANCE_BY_CHECK[check_name] for check_name in failures if check_name in _GUIDANCE_BY_CHECK],
        "rerender_bundle": _rerender_bundle(bucket_name, next_action, rerender_reasons, rerender_context_by_shot=rerender_context_by_shot),
        "rerender_prescription": _rerender_prescription(next_action),
    }



def _next_action(failures: list[str], action_priority: tuple[tuple[str, str], ...]) -> str:
    if not failures:
        return "no_action"
    for check_name, action_name in action_priority:
        if check_name in failures:
            return action_name
    return "review_failed_checks"



def _rerender_bundle(
    bucket_name: str,
    action_name: str,
    rerender_reasons: dict[str, list[str]],
    *,
    rerender_context_by_shot: dict[str, dict[str, str]] | None = None,
) -> dict[str, object]:
    if action_name == "no_action":
        return {
            "action": "no_action",
            "target_shots": [],
            "reason_codes": [],
        }
    bucket_reason_codes = _BUCKET_REASON_CODES.get(bucket_name, set())
    target_shots: list[str] = []
    target_material_ids: list[str] = []
    target_section_ids: list[str] = []
    reason_codes: set[str] = set()
    context_by_shot = rerender_context_by_shot if isinstance(rerender_context_by_shot, dict) else {}
    for shot_id, reasons in rerender_reasons.items():
        matched_reasons = [reason for reason in reasons if reason in bucket_reason_codes] if isinstance(reasons, list) else []
        if not matched_reasons:
            continue
        normalized_shot_id = str(shot_id or "").strip()
        if normalized_shot_id:
            target_shots.append(normalized_shot_id)
            context = context_by_shot.get(normalized_shot_id, {})
            material_id = str(context.get("material_id", "")).strip()
            section_id = str(context.get("section_id", "")).strip()
            if material_id and material_id not in target_material_ids:
                target_material_ids.append(material_id)
            if section_id and section_id not in target_section_ids:
                target_section_ids.append(section_id)
        reason_codes.update(str(reason).strip() for reason in matched_reasons if str(reason).strip())
    return {
        "action": action_name,
        "target_shots": target_shots,
        "target_material_ids": target_material_ids,
        "target_section_ids": target_section_ids,
        "reason_codes": sorted(reason_codes),
    }



def _build_rerender_context_by_shot(
    *,
    shot_plan: list[dict],
    material_plan: list[dict],
    render_plan: list[dict],
    still_results: list[dict],
    clip_results: list[dict],
) -> dict[str, dict[str, str]]:
    material_section_by_id = {
        str(row.get("material_id", "")).strip(): str(row.get("section_id", "")).strip()
        for row in material_plan
        if isinstance(row, dict) and str(row.get("material_id", "")).strip()
    }
    shot_map = {
        str(row.get("shot_id", "")).strip(): row
        for row in shot_plan
        if isinstance(row, dict) and str(row.get("shot_id", "")).strip()
    }
    legacy_provenance_by_shot = _build_legacy_manifest_provenance_by_shot(shot_plan)
    render_map = {
        str(row.get("shot_id", "")).strip(): row
        for row in render_plan
        if isinstance(row, dict) and str(row.get("shot_id", "")).strip()
    }
    still_map = {
        str(row.get("shot_id", "")).strip(): row
        for row in still_results
        if isinstance(row, dict) and str(row.get("shot_id", "")).strip()
    }
    clip_map = {
        str(row.get("shot_id", "")).strip(): row
        for row in clip_results
        if isinstance(row, dict) and str(row.get("shot_id", "")).strip()
    }
    shot_ids = [
        shot_id
        for shot_id in [*shot_map.keys(), *render_map.keys(), *still_map.keys(), *clip_map.keys()]
        if shot_id
    ]
    out: dict[str, dict[str, str]] = {}
    for shot_id in shot_ids:
        shot_row = shot_map.get(shot_id, {})
        render_row = render_map.get(shot_id, {})
        still_row = still_map.get(shot_id, {})
        clip_row = clip_map.get(shot_id, {})
        material_id = str(
            clip_row.get("material_id")
            or still_row.get("material_id")
            or render_row.get("material_id")
            or shot_row.get("material_id")
            or ""
        ).strip()
        section_id = str(
            clip_row.get("section_id")
            or still_row.get("section_id")
            or render_row.get("section_id")
            or shot_row.get("section_id")
            or material_section_by_id.get(material_id, "")
            or legacy_provenance_by_shot.get(shot_id, {}).get("section_id", "")
            or ""
        ).strip()
        if not material_id:
            material_id = str(legacy_provenance_by_shot.get(shot_id, {}).get("material_id", "")).strip()
        out[shot_id] = {
            "material_id": material_id,
            "section_id": section_id,
        }
    return out


def _build_legacy_manifest_provenance_by_shot(shot_plan: list[dict]) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for idx, row in enumerate(shot_plan, start=1):
        if not isinstance(row, dict):
            continue
        shot_id = str(row.get("shot_id", "")).strip()
        if not shot_id or not _has_legacy_manifest_section_context(row):
            continue
        out[shot_id] = {
            "material_id": f"MAT_{idx:03d}",
            "section_id": str(row.get("section_id", "")).strip() or f"SEC_{idx:03d}",
        }
    return out



def _has_legacy_manifest_section_context(row: dict) -> bool:
    return bool(str(row.get("section_name", "")).strip() or _int_like(row.get("source_section_index")) is not None)



def _int_like(value: object) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None



def _rerender_prescription(action_name: str, reason_codes: list[str] | None = None) -> dict[str, object]:
    prescriptions = {
        "no_action": {
            "stage_focus": None,
            "workflow_focus": None,
            "prompt_contract_focus": [],
            "fix_strategy": "no_action",
        },
        "rerender_clips_with_terminal_frame_cleanup": {
            "stage_focus": "clips",
            "workflow_focus": ["ia2v"],
            "prompt_contract_focus": ["clip_prompt_seed", "clip_positive_prompt"],
            "fix_strategy": "shorter_motion_and_clean_terminal_frames",
        },
        "rerender_weak_shots_with_prompt_tightening": {
            "stage_focus": "stills",
            "workflow_focus": ["flux2_image"],
            "prompt_contract_focus": ["still_prompt_text"],
            "fix_strategy": "tighten_subject_identity_and_style_anchors",
        },
        "rerender_scene_intrusion_shots": {
            "stage_focus": "stills",
            "workflow_focus": ["flux2_image"],
            "prompt_contract_focus": ["still_prompt_text"],
            "fix_strategy": "tighten_subject_and_world_anchors",
        },
        "rerender_motion_fragile_shots_with_safer_keyframes": {
            "stage_focus": "stills_then_clips",
            "workflow_focus": ["flux2_image", "ia2v"],
            "prompt_contract_focus": ["still_prompt_text", "clip_prompt_seed", "clip_positive_prompt"],
            "fix_strategy": "replace_fragile_keyframes_before_clip_rerender",
        },
        "rerender_panelized_keyframes": {
            "stage_focus": "stills",
            "workflow_focus": ["flux2_image"],
            "prompt_contract_focus": ["still_prompt_text"],
            "fix_strategy": "enforce_single_frame_keyframe_composition",
        },
        "rerender_character_payoff_shots": {
            "stage_focus": "stills_then_clips",
            "workflow_focus": ["flux2_image", "ia2v"],
            "prompt_contract_focus": ["still_prompt_text", "clip_prompt_seed", "clip_positive_prompt"],
            "fix_strategy": "strengthen_character_payoff_and_subject_scale",
        },
        "revise_assembly_weights_before_clip_rerender": {
            "stage_focus": "review",
            "workflow_focus": None,
            "prompt_contract_focus": [],
            "fix_strategy": "revise_assembly_weights_before_clip_rerender",
        },
        "revise_transition_selection": {
            "stage_focus": "review",
            "workflow_focus": None,
            "prompt_contract_focus": [],
            "fix_strategy": "revise_transition_selection",
        },
    }
    prescription = dict(prescriptions.get(action_name, {
        "stage_focus": "review",
        "workflow_focus": None,
        "prompt_contract_focus": [],
        "fix_strategy": "inspect_review_failures_manually",
    }))
    normalized_reasons = {str(reason).strip() for reason in reason_codes or [] if str(reason).strip()}
    if action_name == "rerender_weak_shots_with_prompt_tightening" and (
        "weak_environment_match" in normalized_reasons or "unrelated_scene_intrusion" in normalized_reasons
    ):
        prescription["fix_strategy"] = "tighten_subject_and_world_anchors"
    elif action_name == "rerender_weak_shots_with_prompt_tightening" and "identity_drift" in normalized_reasons:
        prescription["stage_focus"] = "stills_then_clips"
        prescription["workflow_focus"] = ["flux2_image", "ia2v"]
        prescription["prompt_contract_focus"] = ["still_prompt_text", "clip_prompt_seed", "clip_positive_prompt"]
        prescription["fix_strategy"] = "tighten_identity_continuity_anchors"
    elif action_name == "rerender_weak_shots_with_prompt_tightening" and "weak_subject_match" in normalized_reasons:
        prescription["fix_strategy"] = "tighten_subject_identity_anchors"
    elif action_name == "rerender_continuity_break_shots" and {"continuity_break", "identity_drift"}.issubset(normalized_reasons):
        prescription["stage_focus"] = "stills_then_clips"
        prescription["workflow_focus"] = ["flux2_image", "ia2v"]
        prescription["prompt_contract_focus"] = ["still_prompt_text", "clip_prompt_seed", "clip_positive_prompt"]
        prescription["fix_strategy"] = "tighten_identity_continuity_anchors"
    return prescription



def _lookup_check(check_name: str, blocking_checks: dict[str, bool], non_blocking_checks: dict[str, bool]) -> bool | None:
    if check_name in blocking_checks:
        return bool(blocking_checks[check_name])
    if check_name in non_blocking_checks:
        return bool(non_blocking_checks[check_name])
    return None



def _check_group_score(
    check_names: tuple[str, ...],
    blocking_checks: dict[str, bool],
    non_blocking_checks: dict[str, bool],
    assembly_quality_summary: dict[str, object] | None,
) -> float:
    assembly = assembly_quality_summary if isinstance(assembly_quality_summary, dict) else None
    values: list[float] = []
    for check_name in check_names:
        if assembly is not None and check_name in assembly:
            values.append(1.0 if bool(assembly.get(check_name)) else 0.0)
            continue
        value = _lookup_check(check_name, blocking_checks, non_blocking_checks)
        if value is None:
            continue
        values.append(1.0 if value else 0.0)
    return round((sum(values) / len(values)) * 100.0, 2) if values else 0.0



def _final_mv_quality_score(
    blocking_checks: dict[str, bool],
    non_blocking_checks: dict[str, bool],
    assembly_quality_summary: dict[str, object],
    technical_completion_score: float,
) -> float:
    section_readability_score = max(0.0, min(1.0, technical_completion_score / 100.0))
    chorus_emphasis_score = _assembly_float(assembly_quality_summary, "chorus_emphasis_score", 0.0)
    transition_intentionality_score = _assembly_float(assembly_quality_summary, "transition_intentionality_score", 0.0)
    continuity_score = _average_check_score(
        ("visual_continuity_preserved", "subject_match_preserved", "environment_match_preserved"),
        blocking_checks,
        non_blocking_checks,
    )
    lane_identity_score = _average_check_score(
        ("style_constraints_respected", "style_identity"),
        blocking_checks,
        non_blocking_checks,
    )
    slideshow_risk_score = _assembly_float(assembly_quality_summary, "slideshow_risk_score", 1.0)
    character_payoff_score = _average_check_score(
        ("character_payoff_present", "background_dominance_within_threshold"),
        blocking_checks,
        non_blocking_checks,
    )
    has_repetition_signals = all(
        key in assembly_quality_summary
        for key in ("cadence_variety_score", "snap_variety_score", "repetitive_edit_risk_score")
    )
    if not has_repetition_signals:
        score = (
            0.20 * section_readability_score
            + 0.18 * chorus_emphasis_score
            + 0.16 * transition_intentionality_score
            + 0.14 * continuity_score
            + 0.12 * lane_identity_score
            + 0.12 * character_payoff_score
            + 0.08 * (1.0 - slideshow_risk_score)
        )
        return round(max(0.0, min(1.0, score)) * 100.0, 2)

    cadence_variety_score = _assembly_float(assembly_quality_summary, "cadence_variety_score", 1.0)
    snap_variety_score = _assembly_float(assembly_quality_summary, "snap_variety_score", 1.0)
    repetitive_edit_risk_score = _assembly_float(assembly_quality_summary, "repetitive_edit_risk_score", 0.0)
    score = (
        0.17 * section_readability_score
        + 0.16 * chorus_emphasis_score
        + 0.12 * transition_intentionality_score
        + 0.11 * cadence_variety_score
        + 0.07 * snap_variety_score
        + 0.10 * continuity_score
        + 0.10 * lane_identity_score
        + 0.11 * character_payoff_score
        + 0.06 * (1.0 - slideshow_risk_score)
        + 0.10 * (1.0 - repetitive_edit_risk_score)
    )
    return round(max(0.0, min(1.0, score)) * 100.0, 2)



def _average_check_score(
    check_names: tuple[str, ...],
    blocking_checks: dict[str, bool],
    non_blocking_checks: dict[str, bool],
) -> float:
    values = [
        1.0 if _lookup_check(check_name, blocking_checks, non_blocking_checks) else 0.0
        for check_name in check_names
    ]
    return round(sum(values) / len(values), 3) if values else 0.0



def _assembly_float(assembly_quality_summary: dict[str, object], key: str, default: float) -> float:
    try:
        value = float(assembly_quality_summary.get(key, default))
    except Exception:
        return default
    return max(0.0, min(1.0, value))



def _publishability_tier(
    blocking_checks: dict[str, bool],
    non_blocking_checks: dict[str, bool],
    final_mv_quality_score: float,
) -> str:
    if any(value is False for value in blocking_checks.values()):
        return "draft_only"
    non_fatal_weaknesses = sum(1 for value in non_blocking_checks.values() if value is False)
    if final_mv_quality_score >= 78.0 and non_fatal_weaknesses == 0:
        return "publishable"
    if final_mv_quality_score >= 66.0 and non_fatal_weaknesses <= 1:
        return "near_publishable"
    return "draft_only"



def _recommended_next_action(publishability_summary: dict[str, dict[str, object]], publishability_tier: str) -> str:
    if publishability_tier == "publishable":
        return "publish"
    for bucket_name in ("technical_completion", "isolated_asset_quality", "final_mv_publishability"):
        bucket = publishability_summary.get(bucket_name)
        if not isinstance(bucket, dict):
            continue
        action = str(bucket.get("next_action", "")).strip()
        if action and action != "no_action":
            return action
    return "review_failed_checks"
