from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from ai_mv.utils.json_utils import read_json

PROJECT_ROOT = Path(__file__).resolve().parents[4]


def runs_root() -> Path:
    root = PROJECT_ROOT / "artifacts" / "runs_state"
    root.mkdir(parents=True, exist_ok=True)
    return root


def ensure_run_dir(run_id: str | None, allow_existing: bool = False) -> Path:
    if str(run_id or "").strip():
        return _explicit_run_dir(str(run_id).strip(), allow_existing)
    return _generated_run_dir()


def init_run_state(config: dict[str, Any], run_id: str | None, allow_existing: bool = False) -> dict[str, Any]:
    run_dir = ensure_run_dir(run_id, allow_existing=allow_existing)
    return {
        "run_id": run_dir.name,
        "status": "running",
        "current_stage": "",
        "failure_reason": "",
        "completed_stages": [],
    }


def read_snapshot(run_id: str) -> dict[str, Any]:
    snap = runs_root() / run_id / "snapshot.json"
    if not snap.exists():
        return {
            "run_id": run_id,
            "status": "missing",
            "current_stage": "",
            "failure_reason": "",
            "completed_stages": [],
        }
    return read_json(snap)


def _explicit_run_dir(run_id: str, allow_existing: bool) -> Path:
    out = runs_root() / run_id
    if out.exists():
        if allow_existing and out.is_dir():
            return out
        raise RuntimeError(f"run_id already exists: {run_id}")
    out.mkdir(parents=True, exist_ok=False)
    return out


def _generated_run_dir() -> Path:
    stamp = time.strftime("%Y%m%d-%H%M%S")
    for idx in range(100):
        suffix = f"-{idx:02d}" if idx else ""
        out = runs_root() / f"{stamp}{suffix}"
        try:
            out.mkdir(parents=True, exist_ok=False)
            return out
        except FileExistsError:
            continue
    raise RuntimeError("failed to allocate unique run_id")
