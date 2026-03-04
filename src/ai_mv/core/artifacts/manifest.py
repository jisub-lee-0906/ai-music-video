from __future__ import annotations

from ai_mv.utils.json_utils import write_json


def write_manifest(state: dict, payload: dict) -> None:
    out = {"run_id": state["run_id"], "status": state["status"], "payload": payload}
    write_json(f"artifacts/runs_state/{state['run_id']}/manifest.json", out)

