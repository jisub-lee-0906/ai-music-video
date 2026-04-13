from __future__ import annotations

from ai_mv.core.state.state_store import read_snapshot


def show_status(run_id: str) -> int:
    snap = read_snapshot(run_id)
    status = snap["status"]
    print(status)
    print(f"completed={len(snap['completed_stages'])}")
    return 0 if status != "missing" else 1
