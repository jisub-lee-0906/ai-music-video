from __future__ import annotations

from ai_mv.core.artifacts.paths import latest_file, latest_success_file, run_file
from ai_mv.utils.json_utils import write_json


def write_run_summary(state: dict, summary: dict) -> None:
    scope = str(state.get("scope", "run"))
    write_json(run_file(state["run_id"], "run_summary.json", scope), summary)
    write_json(latest_file("run_summary.json", scope), summary)
    if str(state.get("status", "")) == "done":
        write_json(latest_success_file("run_summary.json", scope), summary)
