from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from ai_mv.core.orchestration.config_defaults import default_config


def load_config(path: str | None = None) -> dict[str, Any]:
    raw = str(path or "").strip()
    if not raw:
        return default_config()
    with Path(raw).open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise RuntimeError("config yaml must be object")
    return data
