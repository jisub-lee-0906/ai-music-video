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
    "motion_fragile_frame",
    "unrelated_scene_intrusion",
    "weak_character_payoff",
    "background_dominant_composition",
)



def quality_findings_review_input_template(shot_ids: list[str] | tuple[str, ...]) -> dict[str, object]:
    normalized: list[str] = []
    for shot_id in shot_ids if isinstance(shot_ids, (list, tuple)) else []:
        value = str(shot_id or "").strip()
        if value and value not in normalized:
            normalized.append(value)
    return {
        "review_inputs": {
            "quality_findings": {shot_id: [] for shot_id in normalized},
        },
        "known_quality_finding_codes": list(KNOWN_QUALITY_FINDING_CODES),
    }
