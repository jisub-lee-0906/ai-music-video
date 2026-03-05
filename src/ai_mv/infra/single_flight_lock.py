from __future__ import annotations

import json
import os
import time
from pathlib import Path

DEFAULT_STALE_SECONDS = 6 * 60 * 60


def acquire_lock(name: str) -> Path:
    lock = Path(f"artifacts/runs_state/{name}.lock")
    lock.parent.mkdir(parents=True, exist_ok=True)
    for _ in range(2):
        fd = _try_create(lock)
        if fd is not None:
            _write_lock(fd)
            return lock
        if not _is_stale(lock):
            raise RuntimeError(f"another run is in progress: {lock}")
        _safe_unlink(lock)
    raise RuntimeError(f"failed to acquire lock: {lock}")


def release_lock(lock: Path) -> None:
    _safe_unlink(lock)


def _try_create(lock: Path) -> int | None:
    try:
        return os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return None


def _write_lock(fd: int) -> None:
    body = {"pid": os.getpid(), "ts": int(time.time())}
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(json.dumps(body))


def _is_stale(lock: Path) -> bool:
    pid, ts = _read_lock(lock)
    if time.time() - ts > DEFAULT_STALE_SECONDS:
        return True
    return not _pid_alive(pid)


def _read_lock(lock: Path) -> tuple[int, int]:
    try:
        data = json.loads(lock.read_text(encoding="utf-8"))
        return int(data.get("pid", -1)), int(data.get("ts", 0))
    except Exception:
        return -1, 0


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _safe_unlink(lock: Path) -> None:
    try:
        lock.unlink()
    except FileNotFoundError:
        return
