from __future__ import annotations


def next_status(current: str, ok: bool) -> str:
    if current == "running" and ok:
        return "running"
    if current == "running" and not ok:
        return "failed"
    return current

