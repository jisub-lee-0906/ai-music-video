from __future__ import annotations

from ai_mv.entrypoints.doctor import run_doctor
from ai_mv.entrypoints.preflight import run_preflight_entry
from ai_mv.entrypoints.start import run_start
from ai_mv.entrypoints.status import show_status
from ai_mv.entrypoints.validate_latest import run_validate_latest


def dispatch(command: str, **kwargs: str) -> int:
    if command == "start":
        return run_start(kwargs.get("run_id"), kwargs.get("concept_text"))
    if command == "doctor":
        return run_doctor()
    if command == "preflight":
        return run_preflight_entry(kwargs.get("run_id"), kwargs.get("concept_text"))
    if command == "status":
        return show_status(kwargs["run_id"])
    if command == "validate-latest":
        return run_validate_latest(kwargs["output_dir"], int(kwargs.get("sample_count", 8) or 8), kwargs.get("shot_ids", []))
    raise ValueError(f"Unsupported command: {command}")
