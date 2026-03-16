from __future__ import annotations

from pathlib import Path

from ai_mv.core.artifacts.prompt_compare_report import write_prompt_compare_report
from ai_mv.core.orchestration.config_defaults import default_config
from ai_mv.core.orchestration.transitions import bootstrap_config


def run_prompt_compare_entry(before_run_id: str, after_run_id: str, profile: str | None = None) -> int:
    cfg = _load_prepared_config(profile)
    report = write_prompt_compare_report(before_run_id, after_run_id, str(cfg.get("profile", "")).strip(), cfg)
    print(f"profile={report['profile']}")
    print(f"overall_alignment={report['overall_alignment']}")
    return 0


def _load_prepared_config(profile: str | None) -> dict:
    cfg = default_config()
    if str(profile or "").strip():
        cfg["profile"] = str(profile).strip()
    return bootstrap_config(cfg, Path.cwd())
