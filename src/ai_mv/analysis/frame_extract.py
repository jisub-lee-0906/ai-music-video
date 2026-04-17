from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from ai_mv.utils.time_utils import ffprobe_duration


TAIL_FRAME_EPSILON_SEC = 0.04


def representative_frame_plan(
    *,
    video_path: str | Path,
    output_dir: str | Path,
    kind: str,
    sample_count: int = 6,
    duration_fn=ffprobe_duration,
) -> list[dict[str, object]]:
    video = Path(video_path)
    out_dir = Path(output_dir)
    duration_sec = float(duration_fn(video))
    if duration_sec <= 0:
        raise RuntimeError(f"unable to determine duration for video: {video}")
    if kind == "clip":
        return [
            _frame_row("first", 0.0, out_dir / "first.png"),
            _frame_row("middle", duration_sec / 2.0, out_dir / "middle.png"),
            _frame_row("last", max(duration_sec - TAIL_FRAME_EPSILON_SEC, 0.0), out_dir / "last.png"),
        ]
    if kind == "final":
        count = max(1, int(sample_count or 1))
        interval = duration_sec / float(count + 1)
        return [
            _frame_row(f"final_{index:02d}", interval * index, out_dir / f"final_{index:02d}.png")
            for index in range(1, count + 1)
        ]
    raise ValueError(f"unsupported frame extraction kind: {kind}")



def extract_frames(
    *,
    video_path: str | Path,
    output_dir: str | Path,
    kind: str,
    sample_count: int = 6,
    duration_fn=ffprobe_duration,
    run_fn=subprocess.run,
) -> list[Path]:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required for frame extraction")
    video = Path(video_path)
    if not video.exists():
        raise RuntimeError(f"video does not exist: {video}")
    plan = representative_frame_plan(
        video_path=video,
        output_dir=output_dir,
        kind=kind,
        sample_count=sample_count,
        duration_fn=duration_fn,
    )
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for row in plan:
        output_path = Path(row["output_path"])
        cmd = build_ffmpeg_frame_extract_cmd(
            ffmpeg=ffmpeg,
            video_path=video,
            timestamp_sec=float(row["timestamp_sec"]),
            output_path=output_path,
        )
        result = run_fn(cmd, check=False, capture_output=True, text=True)
        if getattr(result, "returncode", 1) != 0:
            detail = (getattr(result, "stderr", "") or "").strip() or (getattr(result, "stdout", "") or "").strip() or "ffmpeg frame extraction failed"
            raise RuntimeError(f"frame extraction failed for {output_path.name}: {detail}")
        written.append(output_path)
    return written



def build_ffmpeg_frame_extract_cmd(
    *,
    ffmpeg: str,
    video_path: str | Path,
    timestamp_sec: float,
    output_path: str | Path,
) -> list[str]:
    return [
        str(ffmpeg),
        "-y",
        "-ss",
        f"{max(float(timestamp_sec), 0.0):.3f}",
        "-i",
        str(video_path),
        "-frames:v",
        "1",
        str(output_path),
    ]



def _frame_row(label: str, timestamp_sec: float, output_path: Path) -> dict[str, object]:
    return {
        "label": label,
        "timestamp_sec": round(max(float(timestamp_sec), 0.0), 3),
        "output_path": output_path,
    }
