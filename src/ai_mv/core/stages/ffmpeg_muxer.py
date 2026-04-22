from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

from ai_mv.utils.text_utils import parse_target


def run_ffmpeg_mux(
    clips: list[dict[str, Any]],
    audio: Path,
    out: Path,
    config: dict,
    timeout_sec: int = 1800,
) -> bool:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg or not clips or not audio.exists():
        return False
    out.parent.mkdir(parents=True, exist_ok=True)
    concat = out.parent / "concat.txt"
    temp_out = out.with_suffix(".tmp.mp4")
    try:
        concat.write_text("\n".join(_concat_block(item) for item in clips), encoding="utf-8")
        w, h, fps = parse_target(str(config["video"]["target"]))
        cmd = _ffmpeg_cmd(ffmpeg, concat, audio, temp_out, str(w), str(h), fps)
        try:
            result = subprocess.run(
                cmd,
                check=False,
                capture_output=True,
                text=True,
                timeout=timeout_sec,
            )
        except subprocess.TimeoutExpired as exc:
            detail = ((exc.stderr or "").strip() or (exc.stdout or "").strip() or "ffmpeg timed out").strip()
            raise RuntimeError(f"ffmpeg merge timed out after {timeout_sec}s: {detail}") from exc
        if result.returncode != 0:
            detail = (result.stderr or "").strip() or (result.stdout or "").strip() or "ffmpeg merge failed"
            raise RuntimeError(f"ffmpeg merge failed with exit code {result.returncode}: {detail}")
        if not temp_out.exists():
            raise RuntimeError("ffmpeg merge failed: output file was not created")
        temp_out.replace(out)
        return True
    finally:
        temp_out.unlink(missing_ok=True)
        concat.unlink(missing_ok=True)


def _ffmpeg_cmd(ffmpeg: str, concat: Path, audio: Path, out: Path, w: str, h: str, fps: int) -> list[str]:
    return [
        ffmpeg,
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat),
        "-i",
        str(audio),
        "-vf",
        f"scale={w}:{h}",
        "-r",
        str(fps),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-shortest",
        str(out),
    ]


def _concat_block(item: dict[str, Any]) -> str:
    path = Path(item["path"])
    safe = path.as_posix().replace("'", "'\\''")
    lines = [f"file '{safe}'"]
    trim_start_sec = item.get("trim_start_sec")
    trim_end_sec = item.get("trim_end_sec")
    if trim_start_sec is not None:
        lines.append(f"inpoint {trim_start_sec}")
    if trim_end_sec is not None:
        lines.append(f"outpoint {trim_end_sec}")
    return "\n".join(lines)
