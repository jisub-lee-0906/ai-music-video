from __future__ import annotations

from ai_mv.entrypoints.doctor import run_doctor
from ai_mv.entrypoints.run_batch import run_batch
from ai_mv.entrypoints.start import run_start
from ai_mv.entrypoints.status import show_status


def dispatch(command: str, **kwargs: str) -> int:
    if command == "start":
        return run_start(kwargs["config"], kwargs.get("run_id"))
    if command == "run-batch":
        return run_batch(kwargs["config"], kwargs.get("run_id"))
    if command == "doctor":
        return run_doctor(kwargs["config"])
    if command == "status":
        return show_status(kwargs["run_id"])
    raise ValueError(f"Unsupported command: {command}")
