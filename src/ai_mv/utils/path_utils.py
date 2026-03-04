from __future__ import annotations

from pathlib import Path


def abs_path(path: str) -> str:
    return str(Path(path).resolve())

