from __future__ import annotations

from ai_mv.core.orchestration.config_defaults import default_config
from ai_mv.core.orchestration.preflight_v2 import run_preflight_v2
from ai_mv.core.orchestration.bootstrap_guard import apply_director_brief, validate_sizes, validate_templates
from ai_mv.core.state.state_store import ensure_run_dir, read_snapshot
from ai_mv.infra.single_flight_lock import acquire_lock, release_lock


def run_preflight_v2_entry(run_id: str | None = None, brief: str | None = None) -> int:
    rid = run_id or ""
    lock = acquire_lock("preflight-v2")
    try:
        cfg = _load_prepared_config(brief)
        rid = _prepare_run_brief(cfg, rid)
        try:
            run_preflight_v2(cfg, rid, allow_existing_run=True)
            print(f"run_id={rid}")
            print("status=done")
            return 0
        except Exception:
            snap = read_snapshot(rid, scope="preflight")
            print(f"run_id={rid}")
            print(f"status={snap['status']}")
            print(f"failure_reason={snap['failure_reason']}")
            return 1
    finally:
        release_lock(lock)


def _load_prepared_config(brief: str | None) -> dict:
    cfg = default_config()
    if str(brief or "").strip():
        cfg["brief"] = str(brief).strip()
    else:
        cfg["brief"] = "director_brief_example"
    # apply_defaults first, then v2 brief bootstrap instead of v1 profile bootstrap
    from ai_mv.core.orchestration.config_defaults import apply_defaults

    apply_defaults(cfg)
    apply_director_brief(cfg)
    validate_sizes(cfg)
    validate_templates(cfg)
    return cfg


def _prepare_run_brief(cfg: dict, run_id: str) -> str:
    run_dir = ensure_run_dir(run_id, allow_existing=False, scope="preflight")
    rid = run_dir.name
    brief = str(cfg.get("brief", "")).strip()
    if brief:
        (run_dir / "selected_brief.txt").write_text(brief, encoding="utf-8")
    return rid
