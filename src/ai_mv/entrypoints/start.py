from __future__ import annotations

from pathlib import Path

from ai_mv.core.orchestration.config_defaults import default_config
from ai_mv.core.orchestration.pipeline import run_pipeline
from ai_mv.core.orchestration.transitions import bootstrap_config
from ai_mv.core.state.state_store import ensure_run_dir, read_snapshot
from ai_mv.entrypoints.doctor import run_doctor
from ai_mv.infra.single_flight_lock import acquire_lock, release_lock


def run_start(run_id: str | None = None, profile: str | None = None) -> int:
    rid = run_id or ""
    lock = acquire_lock("start")
    try:
        cfg = _load_prepared_config(profile)
        if _run_doctor_with_profile(cfg) != 0:
            return 1
        rid = _prepare_run_profile(cfg, rid)
        run_pipeline(cfg, rid, allow_existing_run=True)
        snap = read_snapshot(rid)
        print(f"run_id={rid}")
        print(f"status={snap['status']}")
        print(f"failure_reason={snap['failure_reason']}")
        return 0 if snap["status"] == "done" else 1
    finally:
        release_lock(lock)


def _load_prepared_config(profile: str | None) -> dict:
    cfg = default_config()
    if str(profile or "").strip():
        cfg["profile"] = str(profile).strip()
    return bootstrap_config(cfg, Path.cwd())


def _run_doctor_with_profile(cfg: dict) -> int:
    return run_doctor(cfg)


def _prepare_run_profile(cfg: dict, run_id: str) -> str:
    run_dir = ensure_run_dir(run_id, allow_existing=False)
    rid = run_dir.name
    profile = str(cfg.get("profile", "")).strip()
    if profile:
        (run_dir / "selected_profile.txt").write_text(profile, encoding="utf-8")
    return rid
