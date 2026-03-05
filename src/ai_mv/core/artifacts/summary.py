from __future__ import annotations

from ai_mv.utils.json_utils import write_json


def write_summary(state: dict, payload: dict) -> None:
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
    write_json(f"artifacts/reports/{state['run_id']}_summary.json", summary)
