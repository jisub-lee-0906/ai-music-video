from __future__ import annotations

from ai_mv.utils.json_utils import write_json


def write_dashboard(state: dict, payload: dict) -> None:
    data = {
        "run_id": state["run_id"],
        "status": state["status"],
        "stages": state["completed_stages"],
        "quality": payload["quality_score"],
    }
    write_json(f"artifacts/dashboards/{state['run_id']}.json", data)
