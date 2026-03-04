from __future__ import annotations

from ai_mv.core.state.state_store import read_snapshot


def show_status(run_id: str) -> int:
    snap = read_snapshot(run_id)
    print(snap.get("status", "unknown"))
    print(f"completed={len(snap.get('completed_stages', []))}")
    return 0

