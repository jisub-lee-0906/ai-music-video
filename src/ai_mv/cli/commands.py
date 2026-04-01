from __future__ import annotations

from ai_mv.entrypoints.doctor import run_doctor
from ai_mv.entrypoints.preflight_v2 import run_preflight_v2_entry
from ai_mv.entrypoints.ref_v2_probe import run_ref_v2_probe
from ai_mv.entrypoints.ref_v2_probe_batch import run_ref_v2_probe_batch
from ai_mv.entrypoints.start_v2 import run_start_v2
from ai_mv.entrypoints.status import show_status
from ai_mv.entrypoints.tti_v2 import run_tti_v2


def dispatch(command: str, **kwargs: str) -> int:
    if command == "start-v2":
        return run_start_v2(kwargs.get("run_id"), kwargs.get("brief"))
    if command == "tti-v2":
        return run_tti_v2(kwargs.get("run_id"), kwargs.get("brief"))
    if command == "ref-v2-probe":
        return run_ref_v2_probe(
            kwargs.get("run_id"),
            kwargs.get("brief"),
            kwargs["ref"],
            kwargs["prompt"],
            kwargs.get("shot_id"),
            kwargs.get("frame_name"),
        )
    if command == "ref-v2-probe-batch":
        return run_ref_v2_probe_batch(
            kwargs.get("run_id"),
            kwargs.get("brief"),
            kwargs["ref"],
            kwargs["prompts_file"],
            kwargs.get("shot_id_prefix"),
            kwargs.get("frame_name"),
        )
    if command == "doctor":
        return run_doctor()
    if command == "preflight-v2":
        return run_preflight_v2_entry(kwargs.get("run_id"), kwargs.get("brief"))
    if command == "status":
        return show_status(kwargs["run_id"])
    raise ValueError(f"Unsupported command: {command}")
