from __future__ import annotations

from ai_mv.core.artifacts.manifest import write_manifest
from ai_mv.core.artifacts.run_summary import write_run_summary


def write_pipeline_artifacts(state: dict, payload: dict, config: dict) -> None:
    write_manifest(state, payload)
    summary = {
        "run_id": state["run_id"],
        "scope": str(state.get("scope", "run")),
        "status": str(state.get("status", "")),
        "current_stage": str(state.get("current_stage", "")),
        "failure_reason": str(state.get("failure_reason", "")),
        "completed_stages": list(state.get("completed_stages", [])),
        "concept_text": str(payload.get("concept_text", "")).strip(),
        "final_video": str(payload.get("final_video", "")).strip(),
        "music_file": str(payload.get("music_file", "")).strip(),
        "review_status": str(payload.get("review_report", {}).get("status", "")).strip()
        if isinstance(payload.get("review_report"), dict)
        else "",
        "rerender_target_count": len(payload.get("review_report", {}).get("rerender_targets", []))
        if isinstance(payload.get("review_report"), dict)
        else 0,
    }
    write_run_summary(state, summary)
