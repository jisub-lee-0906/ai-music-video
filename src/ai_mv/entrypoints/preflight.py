from __future__ import annotations

from ai_mv.core.artifacts.paths import run_file
from ai_mv.core.orchestration.bootstrap_guard import apply_citypop_defaults, validate_sizes, validate_templates
from ai_mv.core.orchestration.config_defaults import apply_defaults, default_config
from ai_mv.core.orchestration.preflight import run_preflight
from ai_mv.core.orchestration.wsl_overrides import apply_wsl_runtime_overrides
from ai_mv.core.state.state_store import ensure_run_dir, read_snapshot
from ai_mv.infra.single_flight_lock import acquire_lock, release_lock


def run_preflight_entry(
    run_id: str | None = None,
    concept_text: str | None = None,
    audio_brief: str | None = None,
    audio_hook_brief: str | None = None,
) -> int:
    rid = run_id or ""
    lock = acquire_lock("preflight")
    try:
        cfg = _load_prepared_config(concept_text, audio_brief, audio_hook_brief)
        rid = _prepare_run_brief(cfg, rid)
        try:
            run_preflight(cfg, rid, allow_existing_run=True)
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


def _load_prepared_config(
    concept_text: str | None,
    audio_brief: str | None = None,
    audio_hook_brief: str | None = None,
) -> dict:
    cfg = default_config()
    if str(concept_text or "").strip():
        cfg["concept_text"] = str(concept_text).strip()
    audio_cfg = cfg.get("audio") if isinstance(cfg.get("audio"), dict) else {}
    if isinstance(audio_cfg, dict):
        if str(audio_brief or "").strip():
            audio_cfg["brief"] = str(audio_brief).strip()
        if str(audio_hook_brief or "").strip():
            audio_cfg["hook_brief"] = str(audio_hook_brief).strip()
    apply_defaults(cfg)
    apply_wsl_runtime_overrides(cfg)
    apply_citypop_defaults(cfg)
    validate_sizes(cfg)
    validate_templates(cfg)
    return cfg


def _prepare_run_brief(cfg: dict, run_id: str) -> str:
    run_dir = ensure_run_dir(run_id, allow_existing=False, scope="preflight")
    rid = run_dir.name
    concept_text = str(cfg.get("concept_text", "")).strip()
    audio_cfg = cfg.get("audio", {}) if isinstance(cfg, dict) else {}
    audio_brief = str(audio_cfg.get("brief", "")).strip() if isinstance(audio_cfg, dict) else ""
    audio_hook_brief = str(audio_cfg.get("hook_brief", "")).strip() if isinstance(audio_cfg, dict) else ""
    if concept_text:
        (run_dir / "concept_text.txt").write_text(concept_text, encoding="utf-8")
        artifact_text = run_file(rid, "inputs/concept_text.txt", scope="preflight")
        artifact_text.parent.mkdir(parents=True, exist_ok=True)
        artifact_text.write_text(concept_text, encoding="utf-8")
    if audio_brief:
        (run_dir / "audio_brief.txt").write_text(audio_brief, encoding="utf-8")
        artifact_text = run_file(rid, "inputs/audio_brief.txt", scope="preflight")
        artifact_text.parent.mkdir(parents=True, exist_ok=True)
        artifact_text.write_text(audio_brief, encoding="utf-8")
    if audio_hook_brief:
        (run_dir / "audio_hook_brief.txt").write_text(audio_hook_brief, encoding="utf-8")
        artifact_text = run_file(rid, "inputs/audio_hook_brief.txt", scope="preflight")
        artifact_text.parent.mkdir(parents=True, exist_ok=True)
        artifact_text.write_text(audio_hook_brief, encoding="utf-8")
    return rid
