from __future__ import annotations

from ai_mv.utils.json_utils import write_json


def write_dashboard(state: dict, payload: dict) -> None:
    score = payload.get("quality_score", 0.0)
    data = {
        "run_id": state["run_id"],
        "status": state["status"],
        "stages": list(state.get("completed_stages", [])),
        "quality": float(score),
    }
    write_json(f"artifacts/dashboards/{state['run_id']}.json", data)
