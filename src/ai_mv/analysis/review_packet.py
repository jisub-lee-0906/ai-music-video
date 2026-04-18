from __future__ import annotations

import json
from pathlib import Path

from ai_mv.analysis.contact_sheet import build_contact_sheet_manifest
from ai_mv.analysis.frame_extract import representative_frame_plan
from ai_mv.core.review.quality_findings import quality_findings_review_input_template



def build_review_packet_manifest(
    *,
    video_path: str | Path,
    output_dir: str | Path,
    kind: str,
    shot_ids: list[str] | tuple[str, ...],
    sample_count: int = 6,
    duration_fn=None,
) -> dict[str, object]:
    output_root = Path(output_dir)
    frames_dir = output_root / "frames"
    plan = representative_frame_plan(
        video_path=video_path,
        output_dir=frames_dir,
        kind=kind,
        sample_count=sample_count,
        duration_fn=duration_fn,
    )
    normalized_shot_ids = _normalize_shot_ids(shot_ids)
    return {
        "video_path": str(Path(video_path)),
        "kind": str(kind),
        "sample_count": int(sample_count or 0),
        "shot_ids": normalized_shot_ids,
        "frame_paths": [str(Path(row["output_path"])) for row in plan],
        "frame_labels": [str(row["label"]) for row in plan],
        "frame_count": len(plan),
        "reviewer_summary": f"Review packet for {len(normalized_shot_ids)} shots with {len(plan)} extracted frames",
        "quality_findings_path": str(output_root / "review-findings.json"),
        "reviewer_notes_path": str(output_root / "review-notes.md"),
        "contact_sheet_image_path": str(output_root / "contact-sheet.png"),
        "contact_sheet_manifest_path": str(output_root / "contact-sheet.json"),
    }



def write_review_packet(
    *,
    video_path: str | Path,
    output_dir: str | Path,
    kind: str,
    shot_ids: list[str] | tuple[str, ...],
    sample_count: int = 6,
    duration_fn=None,
) -> dict[str, Path]:
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    manifest = build_review_packet_manifest(
        video_path=video_path,
        output_dir=output_root,
        kind=kind,
        shot_ids=shot_ids,
        sample_count=sample_count,
        duration_fn=duration_fn,
    )
    manifest_path = output_root / "review-packet.json"
    quality_findings_path = Path(manifest["quality_findings_path"])
    reviewer_notes_path = Path(manifest["reviewer_notes_path"])
    contact_sheet_manifest_path = Path(manifest["contact_sheet_manifest_path"])
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    quality_findings_path.write_text(
        json.dumps(quality_findings_review_input_template(list(manifest["shot_ids"])), indent=2) + "\n",
        encoding="utf-8",
    )
    reviewer_notes_path.write_text(_reviewer_notes_template(manifest), encoding="utf-8")
    contact_sheet_manifest_path.write_text(
        json.dumps(
            build_contact_sheet_manifest(
                frame_paths=list(manifest["frame_paths"]),
                frame_labels=list(manifest["frame_labels"]),
                output_image_path=manifest["contact_sheet_image_path"],
            ),
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "manifest_path": manifest_path,
        "quality_findings_path": quality_findings_path,
        "reviewer_notes_path": reviewer_notes_path,
        "contact_sheet_image_path": Path(manifest["contact_sheet_image_path"]),
        "contact_sheet_manifest_path": contact_sheet_manifest_path,
    }



def _normalize_shot_ids(shot_ids: list[str] | tuple[str, ...]) -> list[str]:
    out: list[str] = []
    for shot_id in shot_ids if isinstance(shot_ids, (list, tuple)) else []:
        value = str(shot_id or "").strip()
        if value and value not in out:
            out.append(value)
    return out



def _reviewer_notes_template(manifest: dict[str, object]) -> str:
    frame_labels = manifest.get("frame_labels", []) if isinstance(manifest, dict) else []
    lines = [
        "# Review Notes",
        "",
        f"- video_path: {manifest.get('video_path', '')}",
        f"- kind: {manifest.get('kind', '')}",
        f"- shot_ids: {', '.join(manifest.get('shot_ids', [])) if isinstance(manifest.get('shot_ids'), list) else ''}",
        f"- frame_labels: {', '.join(frame_labels) if isinstance(frame_labels, list) else ''}",
        "",
        "## Observed issues",
        "- ",
        "",
        "## Notes",
        "- ",
    ]
    return "\n".join(lines) + "\n"
