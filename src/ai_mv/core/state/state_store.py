from __future__ import annotations

import time
from pathlib import Path
import re
from typing import Any

from ai_mv.utils.json_utils import read_json
from ai_mv.utils.project_root import project_root

PROJECT_ROOT = project_root(__file__)


def _scope_name(scope: str) -> str:
    return "preflight" if str(scope).strip().lower() == "preflight" else "run"


def runs_root(scope: str = "run") -> Path:
    folder = "preflight_state" if _scope_name(scope) == "preflight" else "runs_state"
    root = PROJECT_ROOT / "artifacts" / folder
    root.mkdir(parents=True, exist_ok=True)
    return root


def ensure_run_dir(run_id: str | None, allow_existing: bool = False, scope: str = "run") -> Path:
    if str(run_id or "").strip():
        _validate_run_id(str(run_id))
        return _explicit_run_dir(str(run_id).strip(), allow_existing, scope)
    return _generated_run_dir(scope)


def init_run_state(config: dict[str, Any], run_id: str | None, allow_existing: bool = False, scope: str = "run") -> dict[str, Any]:
    run_dir = ensure_run_dir(run_id, allow_existing=allow_existing, scope=scope)
    return {
        "run_id": run_dir.name,
        "scope": _scope_name(scope),
        "status": "running",
        "current_stage": "",
        "failure_reason": "",
        "completed_stages": [],
    }


def read_snapshot(run_id: str, scope: str = "auto") -> dict[str, Any]:
    _validate_run_id(str(run_id))
    scopes = ("run", "preflight") if str(scope).strip().lower() == "auto" else (_scope_name(scope),)
    for item in scopes:
        snap = runs_root(item) / run_id / "snapshot.json"
        if snap.exists():
            return read_json(snap)
    return {
        "run_id": run_id,
        "scope": _scope_name(scope) if str(scope).strip().lower() != "auto" else "",
        "status": "missing",
        "current_stage": "",
        "failure_reason": "",
        "completed_stages": [],
    }


def _explicit_run_dir(run_id: str, allow_existing: bool, scope: str) -> Path:
    _validate_run_id(run_id)
    out = runs_root(scope) / run_id
    if out.exists():
        if allow_existing and out.is_dir():
            return out
        raise RuntimeError(f"run_id already exists: {run_id}")
    out.mkdir(parents=True, exist_ok=False)
    return out


def _validate_run_id(run_id: str) -> None:
    if not re.fullmatch(r"[A-Za-z0-9._-]+", run_id.strip()):
        raise RuntimeError(f"invalid run_id: {run_id}")


def _generated_run_dir(scope: str) -> Path:
    stamp = time.strftime("%Y%m%d-%H%M%S")
    for idx in range(100):
        suffix = f"-{idx:02d}" if idx else ""
        out = runs_root(scope) / f"{stamp}{suffix}"
        try:
            out.mkdir(parents=True, exist_ok=False)
            return out
        except FileExistsError:
            continue
    raise RuntimeError("failed to allocate unique run_id")
