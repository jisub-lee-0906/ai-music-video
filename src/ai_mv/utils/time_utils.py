from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path


def now_id() -> str:
    return time.strftime("%Y%m%d-%H%M%S")


def ffprobe_duration(path: str | Path) -> float:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return 0.0
    cmd = [
        ffprobe,
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        return 0.0
    try:
        return float((result.stdout or "0").strip())
    except ValueError:
        return 0.0
