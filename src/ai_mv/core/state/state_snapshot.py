from __future__ import annotations

from ai_mv.core.state.state_store import runs_root
from ai_mv.utils.json_utils import write_json


def save_snapshot(state: dict, payload: dict) -> None:
    out = runs_root() / state["run_id"] / "snapshot.json"
    write_json(out, {**state, "payload_keys": sorted(list(payload.keys()))})

