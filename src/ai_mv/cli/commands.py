from __future__ import annotations

from ai_mv.entrypoints.doctor import run_doctor
from ai_mv.entrypoints.extract_frames import run_extract_frames
from ai_mv.entrypoints.preflight import run_preflight_entry
from ai_mv.entrypoints.quality_findings_template import run_quality_findings_template
from ai_mv.entrypoints.start import run_start
from ai_mv.entrypoints.status import show_status


def dispatch(command: str, **kwargs: str) -> int:
    if command == "start":
        return run_start(kwargs.get("run_id"), kwargs.get("concept_text"))
    if command == "doctor":
        return run_doctor()
    if command == "preflight":
        return run_preflight_entry(kwargs.get("run_id"), kwargs.get("concept_text"))
    if command == "status":
        return show_status(kwargs["run_id"])
    if command == "extract-frames":
        return run_extract_frames(kwargs["video"], kwargs["output_dir"], kwargs.get("kind", "clip"), int(kwargs.get("sample_count", 6) or 6))
    if command == "quality-findings-template":
        return run_quality_findings_template(kwargs.get("shot_ids", []), kwargs["output"])
    raise ValueError(f"Unsupported command: {command}")
