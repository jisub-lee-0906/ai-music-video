from __future__ import annotations

import tempfile
from pathlib import Path

import yaml

from ai_mv.core.orchestration.pipeline import run_pipeline
from ai_mv.core.orchestration.transitions import bootstrap_config
from ai_mv.core.state.state_store import ensure_run_dir, load_config, read_snapshot
from ai_mv.entrypoints.doctor import run_doctor
from ai_mv.infra.single_flight_lock import acquire_lock, release_lock
from ai_mv.utils.path_utils import abs_path


def run_start(config_path: str | None = None, run_id: str | None = None, profile: str | None = None) -> int:
    rid = run_id or ""
    lock = acquire_lock("start")
    try:
        cfg = _load_prepared_config(config_path, profile)
        if _run_doctor_with_temp_config(cfg) != 0:
            return 1
        cfg_path, rid = _prepare_run_config(cfg, rid)
        run_pipeline(cfg_path, rid, allow_existing_run=True)
        snap = read_snapshot(rid)
        print(f"run_id={rid}")
        print(f"status={snap['status']}")
        print(f"failure_reason={snap['failure_reason']}")
        return 0 if snap["status"] == "done" else 1
    finally:
        release_lock(lock)


def _load_prepared_config(config_path: str | None, profile: str | None) -> dict:
    cfg = load_config(config_path)
    if str(profile or "").strip():
        cfg["profile"] = str(profile).strip()
    base = Path(config_path).resolve().parent if str(config_path or "").strip() else Path.cwd()
    return bootstrap_config(cfg, base)


def _run_doctor_with_temp_config(cfg: dict) -> int:
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".yaml", delete=False) as f:
        yaml.safe_dump(cfg, f, sort_keys=False)
        temp = Path(f.name)
    try:
        return run_doctor(abs_path(str(temp)))
    finally:
        temp.unlink(missing_ok=True)


def _prepare_run_config(cfg: dict, run_id: str) -> tuple[str, str]:
    run_dir = ensure_run_dir(run_id, allow_existing=False)
    rid = run_dir.name
    effective = run_dir / "effective_config.yaml"
    effective.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
    return abs_path(str(effective)), rid
