from __future__ import annotations

from pathlib import Path

from ai_mv.analysis.frame_extract import extract_frames
from ai_mv.analysis.review_packet import write_review_packet
from ai_mv.core.artifacts.paths import latest_success_file
from ai_mv.utils.json_utils import read_json, write_json



def run_validate_latest(
    output_dir: str,
    sample_count: int = 8,
    shot_ids: list[str] | None = None,
    scope: str = "run",
) -> int:
    manifest_path = latest_success_file("manifest.json", scope)
    run_summary_path = latest_success_file("run_summary.json", scope)
    manifest = read_json(manifest_path)
    run_summary = read_json(run_summary_path)
    final_video = str(manifest.get("assembly", {}).get("final_video", "")).strip() if isinstance(manifest.get("assembly"), dict) else ""
    if not final_video:
        raise RuntimeError(f"latest_success manifest missing assembly.final_video: {manifest_path}")
    resolved_output_dir = Path(output_dir)
    frames_dir = resolved_output_dir / "final-frames"
    packet_dir = resolved_output_dir / "review-packet"
    normalized_shot_ids = [str(value).strip() for value in (shot_ids or []) if str(value).strip()]
    written_frames = extract_frames(
        video_path=final_video,
        output_dir=str(frames_dir),
        kind="final",
        sample_count=int(sample_count or 8),
    )
    written_packet = write_review_packet(
        video_path=final_video,
        output_dir=str(packet_dir),
        kind="final",
        sample_count=int(sample_count or 8),
        shot_ids=normalized_shot_ids,
    )
    summary = {
        "run_id": str(manifest.get("run_id", "")).strip() or str(run_summary.get("run_id", "")).strip(),
        "scope": str(scope).strip() or "run",
        "manifest_path": str(manifest_path),
        "run_summary_path": str(run_summary_path),
        "final_video": final_video,
        "frames_dir": str(frames_dir),
        "frames_written": [str(Path(path)) for path in written_frames],
        "review_packet_manifest": str(written_packet["manifest_path"]),
        "review_findings": str(written_packet["quality_findings_path"]),
        "review_notes": str(written_packet["reviewer_notes_path"]),
        "contact_sheet_image": str(written_packet["contact_sheet_image_path"]),
        "contact_sheet_manifest": str(written_packet["contact_sheet_manifest_path"]),
    }
    summary_path = resolved_output_dir / "validation-summary.json"
    write_json(summary_path, summary)
    print(f"run_id={summary['run_id']}")
    print(f"scope={summary['scope']}")
    print(f"manifest={manifest_path}")
    print(f"run_summary={run_summary_path}")
    print(f"final_video={final_video}")
    print(frames_dir)
    print(written_packet["manifest_path"])
    print(summary_path)
    return 0
