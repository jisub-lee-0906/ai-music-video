from __future__ import annotations

from ai_mv.core.artifacts.paths import latest_file, latest_success_file, run_file
from ai_mv.core.artifacts.schema import artifact_schema_version
from ai_mv.core.artifacts.success_policy import latest_success_eligible
from ai_mv.utils.json_utils import write_json


def write_manifest(state: dict, payload: dict) -> None:
    scope = str(state.get("scope", "run"))
    out = {
        "run_id": state["run_id"],
        "status": state["status"],
        "failure_reason": state["failure_reason"],
        "schema_version": artifact_schema_version(),
        "input": {
            "concept_text": str(payload.get("concept_text", "")),
        },
        "song": {
            "music_file": str(payload.get("music_file", "")),
            "audio_plan": dict(payload.get("audio_plan", {})),
            "audio_map": dict(payload.get("audio_map", {})),
        },
        "style_resolution": dict(payload.get("style_resolution", {})) or {
            "style_name": str(payload.get("style_name", "")),
        },
        "sections": list(payload.get("shot_plan", [])),
        "materials": {
            "still_results": list(payload.get("still_results", [])),
        },
        "renders": {
            "render_plan": list(payload.get("render_plan", [])),
            "clip_results": list(payload.get("clip_results", [])),
        },
        "assembly": {
            "final_video": str(payload.get("final_video", "")),
            "review_inputs": dict(payload.get("review_inputs", {})),
        },
        "review": dict(payload.get("review_report", {})),
        "artifacts": {
            "scope": scope,
        },
    }
    write_json(run_file(state["run_id"], "manifest.json", scope), out)
    write_json(latest_file("manifest.json", scope), out)
    if latest_success_eligible(state, payload):
        write_json(latest_success_file("manifest.json", scope), out)
