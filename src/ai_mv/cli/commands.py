from __future__ import annotations

from ai_mv.entrypoints.doctor import run_doctor
from ai_mv.entrypoints.preflight_v2 import run_preflight_v2_entry
from ai_mv.entrypoints.start_v2 import run_start_v2
from ai_mv.entrypoints.status import show_status


def dispatch(command: str, **kwargs: str) -> int:
    if command == "start-v2":
        return run_start_v2(kwargs.get("run_id"), kwargs.get("brief"))
    if command == "doctor":
        return run_doctor()
    if command == "preflight-v2":
        return run_preflight_v2_entry(kwargs.get("run_id"), kwargs.get("brief"))
    if command == "status":
        return show_status(kwargs["run_id"])
    raise ValueError(f"Unsupported command: {command}")
