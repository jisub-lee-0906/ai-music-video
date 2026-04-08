from __future__ import annotations

from pathlib import Path

from ai_mv.core.orchestration.config_defaults import apply_defaults
from ai_mv.core.orchestration.bootstrap_guard import apply_citypop_defaults, validate_sizes, validate_templates


def bootstrap_config(config: dict, run_dir: Path) -> dict:
    apply_defaults(config)
    apply_citypop_defaults(config)
    validate_sizes(config)
    validate_templates(config)
    return config
