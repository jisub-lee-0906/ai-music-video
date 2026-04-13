from __future__ import annotations

from ai_mv.core.artifacts.paths import run_file
from ai_mv.core.state.state_store import runs_root
from ai_mv.utils.json_utils import write_json


def save_snapshot(state: dict, payload: dict) -> None:
    scope = str(state.get("scope", "run"))
    snapshot = {**state, "payload_keys": sorted(list(payload.keys()))}
    out = runs_root(scope) / state["run_id"] / "snapshot.json"
    write_json(out, snapshot)
    write_json(run_file(state["run_id"], "snapshot.json", scope), snapshot)

