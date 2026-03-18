from __future__ import annotations

from pathlib import Path
from ai_mv.utils.project_root import project_root

PROJECT_ROOT = project_root(__file__)


def _scope_name(scope: str) -> str:
    return "preflight" if str(scope).strip().lower() == "preflight" else "run"


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


def preflight_root() -> Path:
    root = artifacts_root() / "preflight"
    root.mkdir(parents=True, exist_ok=True)
    return root


def scoped_runs_root(scope: str = "run") -> Path:
    return preflight_root() if _scope_name(scope) == "preflight" else runs_root()


def latest_root(scope: str = "run") -> Path:
    if _scope_name(scope) == "preflight":
        root = preflight_root() / "latest"
    else:
        root = artifacts_root() / "latest"
    root.mkdir(parents=True, exist_ok=True)
    return root


def latest_success_root(scope: str = "run") -> Path:
    if _scope_name(scope) == "preflight":
        root = preflight_root() / "latest_success"
    else:
        root = artifacts_root() / "latest_success"
    root.mkdir(parents=True, exist_ok=True)
    return root


def run_file(run_id: str, name: str, scope: str = "run") -> Path:
    root = scoped_runs_root(scope) / str(run_id).strip()
    root.mkdir(parents=True, exist_ok=True)
    return root / name


def latest_file(name: str, scope: str = "run") -> Path:
    return latest_root(scope) / name


def latest_success_file(name: str, scope: str = "run") -> Path:
    return latest_success_root(scope) / name
