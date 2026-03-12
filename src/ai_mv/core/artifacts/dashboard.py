from __future__ import annotations

from ai_mv.core.artifacts.paths import latest_file, run_file
from ai_mv.utils.json_utils import write_json


def write_dashboard(state: dict, payload: dict) -> None:
    data = {
        "run_id": state["run_id"],
        "status": state["status"],
        "stages": list(state.get("completed_stages", [])),
    }
    write_json(run_file(state["run_id"], "dashboard.json"), data)
    write_json(latest_file("dashboard.json"), data)
