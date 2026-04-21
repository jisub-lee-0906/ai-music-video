from __future__ import annotations

from ai_mv.core.artifacts.paths import latest_file, latest_success_file, run_file
from ai_mv.core.artifacts.success_policy import latest_success_eligible
from ai_mv.utils.json_utils import write_json


def write_run_summary(state: dict, summary: dict) -> None:
    scope = str(state.get("scope", "run"))
    write_json(run_file(state["run_id"], "run_summary.json", scope), summary)
    write_json(latest_file("run_summary.json", scope), summary)
    if latest_success_eligible(state, summary):
        write_json(latest_success_file("run_summary.json", scope), summary)
