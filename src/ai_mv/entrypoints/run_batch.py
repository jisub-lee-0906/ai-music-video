from __future__ import annotations

from ai_mv.core.orchestration.pipeline import run_pipeline
from ai_mv.core.state.state_store import ensure_run_dir
from ai_mv.utils.path_utils import abs_path


def run_batch(config_path: str, run_id: str | None = None) -> int:
    cfg = abs_path(config_path)
    rid = run_id or ""
    ensure_run_dir(rid)
    run_pipeline(cfg, rid)
    return 0

