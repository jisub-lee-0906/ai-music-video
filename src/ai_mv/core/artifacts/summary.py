from __future__ import annotations

from ai_mv.utils.json_utils import write_json


def write_summary(state: dict, payload: dict) -> None:
    summary = {
        "run_id": state["run_id"],
        "completed_stages": state["completed_stages"],
        "current_stage": state.get("current_stage", ""),
        "failure_reason": state.get("failure_reason", ""),
        "keys": sorted(payload.keys()),
        "shots": len(payload.get("anchors", [])),
        "clips": len(payload.get("clips", [])),
    }
    write_json(f"artifacts/reports/{state['run_id']}_summary.json", summary)
