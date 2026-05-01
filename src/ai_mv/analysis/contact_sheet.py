from __future__ import annotations

import shutil
import subprocess
from math import ceil
from pathlib import Path
from tempfile import TemporaryDirectory



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


def write_contact_sheet_image(
    *,
    frame_paths: list[str | Path],
    output_image_path: str | Path,
    columns: int,
    rows: int,
    run_fn=subprocess.run,
) -> Path:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required for contact sheet generation")
    normalized_frames = [Path(path) for path in frame_paths]
    if not normalized_frames:
        raise RuntimeError("contact sheet requires at least one frame")
    missing = [str(path) for path in normalized_frames if not path.exists()]
    if missing:
        raise RuntimeError(f"contact sheet frame does not exist: {missing[0]}")
    output = Path(output_image_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    tile_columns = max(1, int(columns or 1))
    tile_rows = max(1, int(rows or 1))
    with TemporaryDirectory(prefix="ai_mv_contact_sheet_") as temp_dir:
        temp_root = Path(temp_dir)
        for index, frame in enumerate(normalized_frames, start=1):
            shutil.copyfile(frame, temp_root / f"frame_{index:03d}.png")
        cmd = build_ffmpeg_contact_sheet_cmd(
            ffmpeg=ffmpeg,
            frame_pattern=temp_root / "frame_%03d.png",
            output_image_path=output,
            columns=tile_columns,
            rows=tile_rows,
        )
        result = run_fn(cmd, check=False, capture_output=True, text=True)
        if getattr(result, "returncode", 1) != 0:
            detail = (getattr(result, "stderr", "") or "").strip() or (getattr(result, "stdout", "") or "").strip() or "ffmpeg contact sheet generation failed"
            raise RuntimeError(f"contact sheet generation failed: {detail}")
    if not output.exists():
        raise RuntimeError(f"contact sheet generation did not write output: {output}")
    return output


def build_ffmpeg_contact_sheet_cmd(
    *,
    ffmpeg: str,
    frame_pattern: str | Path,
    output_image_path: str | Path,
    columns: int,
    rows: int,
) -> list[str]:
    return [
        str(ffmpeg),
        "-y",
        "-framerate",
        "1",
        "-i",
        str(frame_pattern),
        "-frames:v",
        "1",
        "-vf",
        f"scale=320:-1,tile={max(1, int(columns or 1))}x{max(1, int(rows or 1))}:padding=8:margin=8",
        str(output_image_path),
    ]



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
    reference_modes = [
        str(reference_mode).strip()
        for reference_mode in context.get("reference_modes", [])
        if str(reference_mode).strip()
    ] if isinstance(context.get("reference_modes"), list) else []
    anchor_source_shot_ids = [
        str(shot_id).strip()
        for shot_id in context.get("anchor_source_shot_ids", [])
        if str(shot_id).strip()
    ] if isinstance(context.get("anchor_source_shot_ids"), list) else []
    followup_shot_ids = [
        str(shot_id).strip()
        for shot_id in context.get("followup_shot_ids", [])
        if str(shot_id).strip()
    ] if isinstance(context.get("followup_shot_ids"), list) else []
    if reference_modes:
        normalized["reference_modes"] = reference_modes
    if anchor_source_shot_ids or "anchor_source_shot_ids" in context:
        normalized["anchor_source_shot_ids"] = anchor_source_shot_ids
    if followup_shot_ids:
        normalized["followup_shot_ids"] = followup_shot_ids
    reference_review_hints = [
        str(value).strip()
        for value in context.get("reference_review_hints", [])
        if str(value).strip()
    ] if isinstance(context.get("reference_review_hints"), list) else []
    if reference_review_hints:
        normalized["reference_review_hints"] = reference_review_hints
    if not any(normalized.values()):
        return {}
    return normalized
