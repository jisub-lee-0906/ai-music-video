from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import yaml

from ai_mv.utils.json_utils import read_json

PROJECT_ROOT = Path(__file__).resolve().parents[4]


def runs_root() -> Path:
    root = PROJECT_ROOT / "artifacts" / "runs_state"
    root.mkdir(parents=True, exist_ok=True)
    return root


def ensure_run_dir(run_id: str | None) -> Path:
    rid = run_id or time.strftime("%Y%m%d-%H%M%S")
    out = runs_root() / rid
    out.mkdir(parents=True, exist_ok=True)
    return out


def init_run_state(config: dict[str, Any], run_id: str | None) -> dict[str, Any]:
    run_dir = ensure_run_dir(run_id)
    return {"run_id": run_dir.name, "status": "running", "completed_stages": []}


def load_config(path: str) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def read_snapshot(run_id: str) -> dict[str, Any]:
    snap = runs_root() / run_id / "snapshot.json"
    if not snap.exists():
        return {"run_id": run_id, "status": "missing", "completed_stages": []}
    return read_json(snap)
