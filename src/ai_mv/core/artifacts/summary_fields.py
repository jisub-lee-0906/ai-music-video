from __future__ import annotations

import math


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        parsed = float(value)
    except Exception:
        return default
    return parsed if math.isfinite(parsed) else default



def derive_summary_fields(payload: dict) -> dict[str, object]:
    style_resolution = payload.get("style_resolution") if isinstance(payload.get("style_resolution"), dict) else {}
    review_report = payload.get("review_report") if isinstance(payload.get("review_report"), dict) else {}
    assembly_revision_summary = review_report.get("assembly_revision_summary") if isinstance(review_report.get("assembly_revision_summary"), dict) else {}
    return {
        "style_lane": str(style_resolution.get("style_lane") or payload.get("style_lane", "")).strip(),
        "style_selection_source": str(style_resolution.get("selection_source", "")).strip(),
        "style_selection_stability": str(style_resolution.get("selection_stability", "")).strip(),
        "style_selection_confidence": _safe_float(style_resolution.get("confidence", 0.0), 0.0),
        "assembly_revision_present": bool(assembly_revision_summary.get("present", False)),
        "assembly_revision_action": str(assembly_revision_summary.get("action", "")).strip(),
        "assembly_revision_target": str(assembly_revision_summary.get("target", "")).strip(),
        "assembly_revision_final_video": str(assembly_revision_summary.get("final_video", "")).strip(),
        "assembly_revision_music_file": str(assembly_revision_summary.get("music_file", "")).strip(),
    }
