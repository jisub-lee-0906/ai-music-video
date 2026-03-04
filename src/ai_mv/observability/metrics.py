from __future__ import annotations

from ai_mv.utils.json_utils import write_json


def write_metrics(run_id: str, metrics: dict) -> None:
    write_json(f"artifacts/reports/{run_id}_metrics.json", metrics)

