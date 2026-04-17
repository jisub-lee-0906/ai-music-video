from __future__ import annotations

BENCHMARK_DIMENSIONS = (
    "alignment",
    "composition",
    "aesthetics",
    "robustness",
    "temporal_coherence",
    "motion_quality",
    "continuity",
    "faithfulness",
)

_REASON_TO_DIMENSIONS = {
    "missing_final_video": ("robustness",),
    "drift_too_high": ("temporal_coherence", "motion_quality"),
    "coverage_too_low": ("robustness",),
    "missing_clip": ("robustness",),
    "missing_still": ("robustness",),
    "terminal_frame_corruption": ("temporal_coherence", "robustness"),
    "continuity_break": ("continuity", "temporal_coherence"),
    "duplicate_subject": ("composition", "faithfulness"),
    "layered_overlay_intrusion": ("composition", "aesthetics"),
    "identity_drift": ("faithfulness", "alignment", "continuity"),
    "weak_subject_match": ("alignment", "faithfulness"),
    "weak_environment_match": ("alignment", "faithfulness"),
    "motion_fragile_frame": ("motion_quality",),
    "unrelated_scene_intrusion": ("alignment", "faithfulness"),
    "panel_layout": ("composition",),
    "collage_layout": ("composition", "aesthetics"),
    "split_screen": ("composition", "aesthetics"),
}


def summarize_benchmark_dimensions(rerender_reasons: dict[str, list[str]]) -> dict[str, dict[str, object]]:
    summary = {
        dimension: {
            "passed": True,
            "affected_shots": [],
            "reasons": [],
        }
        for dimension in BENCHMARK_DIMENSIONS
    }
    for shot_id, reasons in rerender_reasons.items() if isinstance(rerender_reasons, dict) else []:
        normalized_shot_id = str(shot_id or "").strip()
        if not normalized_shot_id:
            continue
        for reason in reasons if isinstance(reasons, list) else []:
            normalized_reason = str(reason or "").strip()
            if not normalized_reason:
                continue
            for dimension in _REASON_TO_DIMENSIONS.get(normalized_reason, ()):
                bucket = summary[dimension]
                bucket["passed"] = False
                if normalized_shot_id not in bucket["affected_shots"]:
                    bucket["affected_shots"].append(normalized_shot_id)
                if normalized_reason not in bucket["reasons"]:
                    bucket["reasons"].append(normalized_reason)
    return summary
