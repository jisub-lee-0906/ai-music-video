from __future__ import annotations

from ai_mv.core.artifacts.paths import latest_file, run_file
from ai_mv.utils.json_utils import write_json


def write_workflow_inputs_preview(state: dict, payload: dict) -> None:
    data = {
        "run_id": state["run_id"],
        "workflow_inputs": dict(payload.get("workflow_inputs_preview", {})),
    }
    write_json(run_file(state["run_id"], "workflow_inputs_preview.json"), data)
    write_json(latest_file("workflow_inputs_preview.json"), data)
