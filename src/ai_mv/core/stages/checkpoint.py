from __future__ import annotations

from ai_mv.core.contracts.stage_io import StageInput
from ai_mv.core.state.state_snapshot import save_snapshot


def checkpoint(stage_input: StageInput, marker: str) -> None:
    payload = dict(stage_input.payload)
    payload["checkpoint"] = marker
    save_snapshot({"run_id": stage_input.run_id, "status": "running"}, payload)

