from __future__ import annotations

from math import ceil
from pathlib import Path



def build_contact_sheet_manifest(
    *,
    frame_paths: list[str | Path],
    frame_labels: list[str],
    output_image_path: str | Path,
    max_columns: int = 4,
    escalation_context: dict[str, object] | None = None,
) -> dict[str, object]:
    normalized_paths = [str(Path(path)) for path in frame_paths]
    normalized_labels = [str(label) for label in frame_labels]
    count = min(len(normalized_paths), len(normalized_labels))
    columns = max(1, min(int(max_columns or 4), max(count, 1)))
    rows = max(1, ceil(count / columns))
    frames: list[dict[str, object]] = []
    for index in range(count):
        frames.append(
            {
                "index": index,
                "label": normalized_labels[index],
                "frame_path": normalized_paths[index],
                "row": index // columns,
                "column": index % columns,
            }
        )
    return {
        "output_image_path": str(Path(output_image_path)),
        "frame_count": count,
        "columns": columns,
        "rows": rows,
        "reviewer_summary": f"Contact sheet with {count} frames across {rows} rows",
        "escalation_context": _normalize_escalation_context(escalation_context),
        "frames": frames,
    }



def _normalize_escalation_context(context: dict[str, object] | None) -> dict[str, object]:
    if not isinstance(context, dict):
        return {}
    normalized = {
        "source_stage": str(context.get("source_stage", "")).strip(),
        "run_id": str(context.get("run_id", "")).strip(),
        "status": str(context.get("status", "")).strip(),
        "shot_ids": [
            str(shot_id).strip()
            for shot_id in context.get("shot_ids", [])
            if str(shot_id).strip()
        ]
        if isinstance(context.get("shot_ids"), list)
        else [],
        "material_ids": [
            str(material_id).strip()
            for material_id in context.get("material_ids", [])
            if str(material_id).strip()
        ]
        if isinstance(context.get("material_ids"), list)
        else [],
        "section_ids": [
            str(section_id).strip()
            for section_id in context.get("section_ids", [])
            if str(section_id).strip()
        ]
        if isinstance(context.get("section_ids"), list)
        else [],
    }
    if not any(normalized.values()):
        return {}
    return normalized
