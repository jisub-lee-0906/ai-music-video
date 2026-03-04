from __future__ import annotations

from pathlib import Path


def acquire_lock(name: str) -> Path:
    lock = Path(f"artifacts/runs_state/{name}.lock")
    lock.parent.mkdir(parents=True, exist_ok=True)
    lock.write_text("locked", encoding="utf-8")
    return lock


def release_lock(lock: Path) -> None:
    if lock.exists():
        lock.unlink()

