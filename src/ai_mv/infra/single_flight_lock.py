from __future__ import annotations

import atexit
import json
import os
import signal
import time
from pathlib import Path

DEFAULT_STALE_SECONDS = 6 * 60 * 60
_LOCKS: set[Path] = set()
_HOOKS_INSTALLED = False
_PREV_HANDLERS: dict[int, object] = {}


def acquire_lock(name: str) -> Path:
    _install_cleanup_hooks()
    lock = Path(f"artifacts/runs_state/{name}.lock")
    lock.parent.mkdir(parents=True, exist_ok=True)
    for _ in range(2):
        fd = _try_create(lock)
        if fd is not None:
            _write_lock(fd)
            _LOCKS.add(lock)
            return lock
        if not _is_stale(lock):
            raise RuntimeError(f"another run is in progress: {lock}")
        _safe_unlink(lock)
    raise RuntimeError(f"failed to acquire lock: {lock}")


def release_lock(lock: Path) -> None:
    _LOCKS.discard(lock)
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
    try:
        pid, ts = _read_lock(lock)
    except Exception:
        return True
    if time.time() - ts > DEFAULT_STALE_SECONDS:
        return True
    return not _pid_alive(pid)


def _read_lock(lock: Path) -> tuple[int, int]:
    try:
        data = json.loads(lock.read_text(encoding="utf-8"))
        return int(data["pid"]), int(data["ts"])
    except Exception:
        raise RuntimeError(f"invalid lock file: {lock}")


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


def _install_cleanup_hooks() -> None:
    global _HOOKS_INSTALLED
    if _HOOKS_INSTALLED:
        return
    atexit.register(_cleanup_locks)
    _attach_signal(signal.SIGINT)
    if hasattr(signal, "SIGTERM"):
        _attach_signal(signal.SIGTERM)
    _HOOKS_INSTALLED = True


def _attach_signal(sig: int) -> None:
    try:
        _PREV_HANDLERS[sig] = signal.getsignal(sig)
        signal.signal(sig, _on_signal)
    except Exception:
        return


def _on_signal(signum: int, _frame) -> None:
    _cleanup_locks()
    prev = _PREV_HANDLERS.get(signum)
    if callable(prev) and prev is not _on_signal:
        prev(signum, _frame)
        return
    raise SystemExit(128 + int(signum))


def _cleanup_locks() -> None:
    for lock in list(_LOCKS):
        _safe_unlink(lock)
        _LOCKS.discard(lock)
