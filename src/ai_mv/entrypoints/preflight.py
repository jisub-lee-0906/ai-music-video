from __future__ import annotations

from pathlib import Path

from ai_mv.core.orchestration.config_defaults import default_config
from ai_mv.core.orchestration.preflight import run_preflight
from ai_mv.core.orchestration.transitions import bootstrap_config
from ai_mv.core.state.state_store import ensure_run_dir
from ai_mv.infra.single_flight_lock import acquire_lock, release_lock


def run_preflight_entry(run_id: str | None = None, profile: str | None = None) -> int:
    rid = run_id or ""
    lock = acquire_lock("preflight")
    try:
        cfg = _load_prepared_config(profile)
        rid = _prepare_run_profile(cfg, rid)
        run_preflight(cfg, rid, allow_existing_run=True)
        print(f"run_id={rid}")
        print("status=done")
        return 0
    finally:
        release_lock(lock)


def _load_prepared_config(profile: str | None) -> dict:
    cfg = default_config()
    if str(profile or "").strip():
        cfg["profile"] = str(profile).strip()
    return bootstrap_config(cfg, Path.cwd())


def _prepare_run_profile(cfg: dict, run_id: str) -> str:
    run_dir = ensure_run_dir(run_id, allow_existing=False, scope="preflight")
    rid = run_dir.name
    profile = str(cfg.get("profile", "")).strip()
    if profile:
        (run_dir / "selected_profile.txt").write_text(profile, encoding="utf-8")
    return rid
