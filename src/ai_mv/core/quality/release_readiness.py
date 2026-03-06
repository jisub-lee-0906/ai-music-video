from __future__ import annotations

from ai_mv.utils.json_utils import write_json


def readiness_report(state: dict, payload: dict) -> None:
    score_raw = payload.get("quality_score")
    score = float(score_raw) if score_raw is not None else 0.0
    has_score = score_raw is not None
    readiness = _readiness_bucket(score, has_score)
    go_live_ready = state["status"] == "done"
    out = {
        "run_id": state["run_id"],
        "status": state["status"],
        "quality_score": score if has_score else None,
        "readiness": readiness,
        "go_live_ready": go_live_ready,
    }
    write_json(f"artifacts/reports/{state['run_id']}_readiness.json", out)


def _readiness_bucket(score: float, has_score: bool) -> str:
    if not has_score:
        return "not_evaluated"
    if score >= 0.95:
        return "excellent"
    if score >= 0.8:
        return "good"
    if score >= 0.6:
        return "fair"
    return "poor"
