from __future__ import annotations

from pathlib import Path

from ai_mv.core.orchestration.bootstrap_content import ensure_lyrics, ensure_run_style
from ai_mv.core.orchestration.config_defaults import apply_defaults
from ai_mv.core.orchestration.bootstrap_guard import apply_profile, validate_sizes, validate_templates


def next_status(current: str, ok: bool) -> str:
    if current == "running" and ok:
        return "running"
    if current == "running" and not ok:
        return "failed"
    return current


def bootstrap_config(config: dict, run_dir: Path) -> dict:
    apply_defaults(config)
    apply_profile(config)
    validate_sizes(config)
    validate_templates(config)
    if bool(config["runtime"]["bootstrap_missing_inputs"]):
        ensure_lyrics(config)
    ensure_run_style(config, run_dir)
    return config
