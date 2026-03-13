from __future__ import annotations

from ai_mv.core.artifacts.paths import latest_file, latest_success_file, run_file
from ai_mv.utils.json_utils import write_json


def write_summary(state: dict, payload: dict) -> None:
    scope = str(state.get("scope", "run"))
    anchors = payload.get("anchors", [])
    clips = payload.get("clips", [])
    summary = {
        "run_id": state["run_id"],
        "completed_stages": list(state.get("completed_stages", [])),
        "current_stage": str(state.get("current_stage", "")),
        "failure_reason": str(state.get("failure_reason", "")),
        "keys": sorted(payload.keys()),
        "shots": len(anchors) if isinstance(anchors, list) else 0,
        "clips": len(clips) if isinstance(clips, list) else 0,
    }
    write_json(run_file(state["run_id"], "summary.json", scope), summary)
    write_json(latest_file("summary.json", scope), summary)
    if str(state.get("status", "")) == "done":
        write_json(latest_success_file("summary.json", scope), summary)
