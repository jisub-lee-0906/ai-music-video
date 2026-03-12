from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[4]


def artifacts_root() -> Path:
    root = PROJECT_ROOT / "artifacts"
    root.mkdir(parents=True, exist_ok=True)
    return root


def reports_root() -> Path:
    root = artifacts_root() / "reports"
    root.mkdir(parents=True, exist_ok=True)
    return root


def runs_root() -> Path:
    root = artifacts_root() / "runs"
    root.mkdir(parents=True, exist_ok=True)
    return root


def latest_root() -> Path:
    root = artifacts_root() / "latest"
    root.mkdir(parents=True, exist_ok=True)
    return root


def run_file(run_id: str, name: str) -> Path:
    root = runs_root() / str(run_id).strip()
    root.mkdir(parents=True, exist_ok=True)
    return root / name


def latest_file(name: str) -> Path:
    return latest_root() / name
