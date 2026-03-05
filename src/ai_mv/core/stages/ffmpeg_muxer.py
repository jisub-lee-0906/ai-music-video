from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def run_ffmpeg_mux(clips: list[Path], audio: Path, out: Path, config: dict) -> bool:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg or not clips or not audio.exists():
        return False
    out.parent.mkdir(parents=True, exist_ok=True)
    concat = out.parent / "concat.txt"
    concat.write_text("\n".join([f"file '{p.as_posix()}'" for p in clips]), encoding="utf-8")
    target = str(config.get("video", {}).get("target", "1920x1080@24"))
    dims, fps = target.split("@")
    w, h = dims.split("x")
    cmd = _ffmpeg_cmd(ffmpeg, concat, audio, out, w, h, int(fps))
    return subprocess.run(cmd, check=False).returncode == 0


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

