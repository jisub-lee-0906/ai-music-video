from __future__ import annotations

from ai_mv.core.orchestration.bootstrap_guard import apply_director_brief, validate_sizes, validate_templates
from ai_mv.core.orchestration.config_defaults import apply_defaults, default_config
from ai_mv.core.orchestration.pipeline import run_pipeline
from ai_mv.core.state.state_store import ensure_run_dir, read_snapshot
from ai_mv.entrypoints.doctor import run_doctor
from ai_mv.infra.single_flight_lock import acquire_lock, release_lock


def run_start(run_id: str | None = None, brief: str | None = None) -> int:
    rid = run_id or ""
    lock = acquire_lock("start")
    try:
        cfg = _load_prepared_config(brief)
        if run_doctor(cfg) != 0:
            return 1
        rid = _prepare_run_brief(cfg, rid)
        run_pipeline(cfg, rid, allow_existing_run=True)
        snap = read_snapshot(rid)
        print(f"run_id={rid}")
        print(f"status={snap['status']}")
        print(f"failure_reason={snap['failure_reason']}")
        return 0 if snap["status"] == "done" else 1
    finally:
        release_lock(lock)


def _load_prepared_config(brief: str | None) -> dict:
    cfg = default_config()
    cfg["brief"] = str(brief or "director_brief_example").strip() or "director_brief_example"
    apply_defaults(cfg)
    apply_director_brief(cfg)
    validate_sizes(cfg)
    validate_templates(cfg)
    return cfg


def _prepare_run_brief(cfg: dict, run_id: str) -> str:
    run_dir = ensure_run_dir(run_id, allow_existing=False)
    rid = run_dir.name
    brief = str(cfg.get("brief", "")).strip()
    if brief:
        (run_dir / "selected_brief.txt").write_text(brief, encoding="utf-8")
    return rid
