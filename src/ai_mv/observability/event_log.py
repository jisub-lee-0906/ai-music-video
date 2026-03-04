from __future__ import annotations

from pathlib import Path
import time


def log_event(run_id: str, msg: str) -> None:
    path = Path(f"artifacts/runs_state/{run_id}/events.log")
    path.parent.mkdir(parents=True, exist_ok=True)
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}\n"
    path.write_text(path.read_text(encoding="utf-8") + line if path.exists() else line, encoding="utf-8")

