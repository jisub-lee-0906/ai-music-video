from __future__ import annotations

from ai_mv.entrypoints.doctor import run_doctor
from ai_mv.entrypoints.preflight import run_preflight_entry
from ai_mv.entrypoints.ref_probe import run_ref_probe
from ai_mv.entrypoints.ref_probe_batch import run_ref_probe_batch
from ai_mv.entrypoints.start import run_start
from ai_mv.entrypoints.status import show_status
from ai_mv.entrypoints.tti import run_tti


def dispatch(command: str, **kwargs: str) -> int:
    if command == "start":
        return run_start(kwargs.get("run_id"), kwargs.get("brief"))
    if command == "tti":
        return run_tti(kwargs.get("run_id"), kwargs.get("brief"))
    if command == "ref-probe":
        return run_ref_probe(
            kwargs.get("run_id"),
            kwargs.get("brief"),
            kwargs["ref"],
            kwargs["prompt"],
            kwargs.get("shot_id"),
            kwargs.get("frame_name"),
        )
    if command == "ref-probe-batch":
        return run_ref_probe_batch(
            kwargs.get("run_id"),
            kwargs.get("brief"),
            kwargs["ref"],
            kwargs["prompts_file"],
            kwargs.get("shot_id_prefix"),
            kwargs.get("frame_name"),
        )
    if command == "doctor":
        return run_doctor()
    if command == "preflight":
        return run_preflight_entry(kwargs.get("run_id"), kwargs.get("brief"))
    if command == "status":
        return show_status(kwargs["run_id"])
    raise ValueError(f"Unsupported command: {command}")
