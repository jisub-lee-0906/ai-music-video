from __future__ import annotations

KNOWN_QUALITY_FINDING_CODES = (
    "terminal_frame_corruption",
    "continuity_break",
    "duplicate_subject",
    "layered_overlay_intrusion",
    "identity_drift",
    "panel_layout",
    "collage_layout",
    "split_screen",
    "weak_subject_match",
    "weak_environment_match",
    "high_risk_interaction_without_backup",
    "red_risk_clip_held_too_long",
    "motion_fragile_frame",
    "unrelated_scene_intrusion",
    "weak_character_payoff",
    "background_dominant_composition",
    "chorus_release_missing",
    "final_payoff_missing",
    "repetitive_safe_editing",
)


def quality_findings_review_input_template(
    shot_ids: list[str] | tuple[str, ...],
    *,
    escalation_context: dict[str, object] | None = None,
) -> dict[str, object]:
    normalized: list[str] = []
    for shot_id in shot_ids if isinstance(shot_ids, (list, tuple)) else []:
        value = str(shot_id or "").strip()
        if value and value not in normalized:
            normalized.append(value)
    review_inputs: dict[str, object] = {
        "quality_findings": {shot_id: [] for shot_id in normalized},
    }
    reference_review_hints = _reference_review_hints(escalation_context)
    if reference_review_hints:
        review_inputs["reference_review_hints"] = reference_review_hints
    return {
        "review_inputs": review_inputs,
        "known_quality_finding_codes": list(KNOWN_QUALITY_FINDING_CODES),
    }


def _reference_review_hints(escalation_context: dict[str, object] | None) -> list[str]:
    if not isinstance(escalation_context, dict):
        return []
    reference_modes = [
        str(value).strip()
        for value in escalation_context.get("reference_modes", [])
        if str(value).strip()
    ] if isinstance(escalation_context.get("reference_modes"), list) else []
    followup_shot_ids = [
        str(value).strip()
        for value in escalation_context.get("followup_shot_ids", [])
        if str(value).strip()
    ] if isinstance(escalation_context.get("followup_shot_ids"), list) else []
    anchor_source_shot_ids = [
        str(value).strip()
        for value in escalation_context.get("anchor_source_shot_ids", [])
        if str(value).strip()
    ] if isinstance(escalation_context.get("anchor_source_shot_ids"), list) else []
    hints: list[str] = []
    if reference_modes:
        hints.append(f"Reference modes in scope: {', '.join(reference_modes)}.")
    if followup_shot_ids:
        hints.append(
            "Follow-up shots to review against their anchor continuity: "
            f"{', '.join(followup_shot_ids)}."
        )
    if anchor_source_shot_ids:
        hints.append(
            "Anchor-source shots to review as continuity baselines: "
            f"{', '.join(anchor_source_shot_ids)}."
        )
    return hints
