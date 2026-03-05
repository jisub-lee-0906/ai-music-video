from __future__ import annotations

from pathlib import Path

import yaml

from ai_mv.core.orchestration.pipeline import run_pipeline
from ai_mv.core.orchestration.transitions import bootstrap_config
from ai_mv.core.state.state_store import ensure_run_dir, read_snapshot
from ai_mv.entrypoints.doctor import run_doctor
from ai_mv.infra.single_flight_lock import acquire_lock, release_lock
from ai_mv.utils.path_utils import abs_path


def run_start(config_path: str, run_id: str | None = None) -> int:
    rid = run_id or ""
    lock = acquire_lock("start")
    try:
        cfg_path, rid, strict_remote = _prepare_config(config_path, rid)
        if strict_remote and run_doctor(cfg_path) != 0:
            return 1
        run_pipeline(cfg_path, rid)
        snap = read_snapshot(rid)
        print(f"run_id={rid}")
        print(f"status={snap.get('status', 'unknown')}")
        print(f"failure_reason={snap.get('failure_reason', '')}")
        return 0 if snap.get("status") == "done" else 1
    finally:
        release_lock(lock)


def _prepare_config(config_path: str, run_id: str) -> tuple[str, str, bool]:
    cfg = yaml.safe_load(Path(config_path).read_text(encoding="utf-8")) or {}
    run_dir = ensure_run_dir(run_id)
    rid = run_dir.name
    cfg = bootstrap_config(cfg, run_dir)
    effective = run_dir / "effective_config.yaml"
    effective.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
    strict_remote = bool(cfg.get("integrations", {}).get("strict_remote", False))
    return abs_path(str(effective)), rid, strict_remote
