from __future__ import annotations

from ai_mv.analysis.review_packet import write_review_packet



def run_review_packet(video: str, output_dir: str, kind: str = "clip", sample_count: int = 6, shot_ids: list[str] | None = None) -> int:
    written = write_review_packet(
        video_path=video,
        output_dir=output_dir,
        kind=kind,
        sample_count=int(sample_count or 6),
        shot_ids=shot_ids or [],
    )
    print(f"video={video}")
    print(f"kind={kind}")
    print(written["manifest_path"])
    print(written["quality_findings_path"])
    print(written["reviewer_notes_path"])
    print(written["contact_sheet_image_path"])
    print(written["contact_sheet_manifest_path"])
    return 0
