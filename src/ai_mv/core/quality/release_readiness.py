from __future__ import annotations

from ai_mv.core.quality.metrics import score_bucket
from ai_mv.utils.json_utils import write_json


def readiness_report(state: dict, payload: dict) -> None:
    score = float(payload.get("quality_score", 0.0))
    out = {
        "run_id": state["run_id"],
        "status": state["status"],
        "quality_score": score,
        "readiness": score_bucket(score),
    }
    write_json(f"artifacts/reports/{state['run_id']}_readiness.json", out)

