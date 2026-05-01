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
    assembly_revision_summary = _assembly_revision_summary(payload)
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
        "assembly_revision_target_shots": [str(value).strip() for value in assembly_revision_summary.get("target_shots", []) if str(value).strip()] if isinstance(assembly_revision_summary.get("target_shots"), list) else [],
        "assembly_revision_target_material_ids": [str(value).strip() for value in assembly_revision_summary.get("target_material_ids", []) if str(value).strip()] if isinstance(assembly_revision_summary.get("target_material_ids"), list) else [],
        "assembly_revision_target_section_ids": [str(value).strip() for value in assembly_revision_summary.get("target_section_ids", []) if str(value).strip()] if isinstance(assembly_revision_summary.get("target_section_ids"), list) else [],
    }



def _assembly_revision_summary(payload: dict) -> dict[str, object]:
    review_report = payload.get("review_report") if isinstance(payload.get("review_report"), dict) else {}
    review_summary = review_report.get("assembly_revision_summary") if isinstance(review_report.get("assembly_revision_summary"), dict) else {}
    revision_result = payload.get("assembly_revision_result") if isinstance(payload.get("assembly_revision_result"), dict) else {}
    if _has_meaningful_assembly_revision_summary(review_summary):
        return dict(review_summary)
    if not revision_result:
        return dict(review_summary) if review_summary else {}
    final_video = str(revision_result.get("output_final_video") or payload.get("final_video", "")).strip()
    music_file = str(revision_result.get("music_file") or payload.get("music_file", "")).strip()
    return {
        "present": True,
        "action": str(revision_result.get("action", "")).strip(),
        "target": str(revision_result.get("target", "")).strip(),
        "final_video": final_video,
        "music_file": music_file,
        "target_shots": [str(value).strip() for value in revision_result.get("target_shots", []) if str(value).strip()] if isinstance(revision_result.get("target_shots"), list) else [],
        "target_material_ids": [str(value).strip() for value in revision_result.get("target_material_ids", []) if str(value).strip()] if isinstance(revision_result.get("target_material_ids"), list) else [],
        "target_section_ids": [str(value).strip() for value in revision_result.get("target_section_ids", []) if str(value).strip()] if isinstance(revision_result.get("target_section_ids"), list) else [],
    }



def _has_meaningful_assembly_revision_summary(summary: object) -> bool:
    if not isinstance(summary, dict):
        return False
    if bool(summary.get("present")):
        return True
    for key in ("action", "target", "final_video", "music_file"):
        if str(summary.get(key, "")).strip():
            return True
    for key in ("target_shots", "target_material_ids", "target_section_ids"):
        value = summary.get(key)
        if isinstance(value, list) and any(str(item).strip() for item in value):
            return True
    return False
