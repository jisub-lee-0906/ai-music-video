from __future__ import annotations

import atexit
import json
import os
import signal
import threading
import time
from dataclasses import dataclass
from pathlib import Path

DEFAULT_STALE_SECONDS = 5 * 60
HEARTBEAT_INTERVAL_SECONDS = 30
_LOCKS: dict[Path, "LockHandle"] = {}
_HOOKS_INSTALLED = False
_PREV_HANDLERS: dict[int, object] = {}


@dataclass
class LockHandle:
    path: Path
    pid: int
    run_id: str
    stop_event: threading.Event
    thread: threading.Thread


def acquire_lock(name: str, run_id: str = "") -> Path:
    _install_cleanup_hooks()
    lock = Path(f"artifacts/runs_state/{name}.lock")
    lock.parent.mkdir(parents=True, exist_ok=True)
    owner = _owner_meta(run_id)
    for _ in range(2):
        fd = _try_create(lock)
        if fd is not None:
            _write_lock(fd, owner)
            handle = _start_heartbeat(lock, owner)
            _LOCKS[lock] = handle
            return lock
        if not _is_stale(lock):
            raise RuntimeError(f"another run is in progress: {lock}")
        _safe_unlink(lock)
    raise RuntimeError(f"failed to acquire lock: {lock}")


def release_lock(lock: Path) -> None:
    handle = _LOCKS.pop(lock, None)
    if handle is not None:
        handle.stop_event.set()
        handle.thread.join(timeout=1.0)
        _safe_release(lock, handle.pid, handle.run_id)
        return
    if not lock.exists():
        return
    meta = _read_lock(lock)
    _safe_release(lock, int(meta["pid"]), str(meta["run_id"]))


def _try_create(lock: Path) -> int | None:
    try:
        return os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return None


def _write_lock(fd: int, owner: dict[str, object]) -> None:
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(json.dumps(owner))


def _rewrite_lock(lock: Path, owner: dict[str, object]) -> None:
    temp = lock.with_suffix(f"{lock.suffix}.tmp")
    temp.write_text(json.dumps(owner), encoding="utf-8")
    temp.replace(lock)


def _start_heartbeat(lock: Path, owner: dict[str, object]) -> LockHandle:
    stop_event = threading.Event()
    thread = threading.Thread(
        target=_heartbeat_loop,
        args=(lock, owner, stop_event),
        daemon=True,
        name=f"lock-heartbeat-{lock.stem}",
    )
    thread.start()
    return LockHandle(
        path=lock,
        pid=int(owner["pid"]),
        run_id=str(owner["run_id"]),
        stop_event=stop_event,
        thread=thread,
    )


def _heartbeat_loop(lock: Path, owner: dict[str, object], stop_event: threading.Event) -> None:
    while not stop_event.wait(HEARTBEAT_INTERVAL_SECONDS):
        try:
            current = _read_lock(lock)
        except Exception:
            return
        if int(current["pid"]) != int(owner["pid"]) or str(current["run_id"]) != str(owner["run_id"]):
            return
        owner["ts"] = int(time.time())
        try:
            _rewrite_lock(lock, owner)
        except Exception:
            return


def _is_stale(lock: Path) -> bool:
    try:
        meta = _read_lock(lock)
    except Exception:
        return True
    ts = int(meta["ts"])
    pid = int(meta["pid"])
    if time.time() - ts > DEFAULT_STALE_SECONDS:
        return True
    return not _pid_alive(pid)


def _read_lock(lock: Path) -> dict[str, object]:
    try:
        data = json.loads(lock.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError(f"invalid lock file: {lock}") from exc
    if not isinstance(data, dict):
        raise RuntimeError(f"invalid lock file: {lock}")
    pid = data.get("pid")
    ts = data.get("ts")
    run_id = data.get("run_id")
    if not isinstance(pid, int) or not isinstance(ts, int) or not isinstance(run_id, str):
        raise RuntimeError(f"invalid lock file: {lock}")
    return {"pid": pid, "ts": ts, "run_id": run_id}


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _safe_release(lock: Path, pid: int, run_id: str) -> None:
    try:
        meta = _read_lock(lock)
    except Exception:
        return
    if int(meta["pid"]) != int(pid) or str(meta["run_id"]) != str(run_id):
        return
    _safe_unlink(lock)


def _safe_unlink(lock: Path) -> None:
    try:
        lock.unlink()
    except FileNotFoundError:
        return


def _owner_meta(run_id: str) -> dict[str, object]:
    return {
        "pid": os.getpid(),
        "run_id": str(run_id).strip(),
        "ts": int(time.time()),
    }


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


def _on_signal(signum: int, frame) -> None:
    _cleanup_locks()
    prev = _PREV_HANDLERS.get(signum)
    if callable(prev) and prev is not _on_signal:
        prev(signum, frame)
        return
    raise SystemExit(128 + int(signum))


def _cleanup_locks() -> None:
    for lock, handle in list(_LOCKS.items()):
        handle.stop_event.set()
        handle.thread.join(timeout=1.0)
        _safe_release(lock, handle.pid, handle.run_id)
        _LOCKS.pop(lock, None)
