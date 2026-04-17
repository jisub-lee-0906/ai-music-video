from __future__ import annotations

from pathlib import Path

from ai_mv.analysis.frame_extract import extract_frames



def run_extract_frames(video: str, output_dir: str, kind: str = "clip", sample_count: int = 6) -> int:
    written = extract_frames(
        video_path=video,
        output_dir=output_dir,
        kind=kind,
        sample_count=int(sample_count or 6),
    )
    print(f"video={video}")
    print(f"kind={kind}")
    print(f"frames_written={len(written)}")
    for path in written:
        print(Path(path))
    return 0
