from __future__ import annotations

from ai_mv.core.artifacts.paths import latest_file, latest_success_file, run_file
from ai_mv.utils.json_utils import write_json


def write_manifest(state: dict, payload: dict) -> None:
    scope = str(state.get("scope", "run"))
    out = {
        "run_id": state["run_id"],
        "status": state["status"],
        "failure_reason": state["failure_reason"],
        "concept_text": str(payload.get("concept_text", "")),
        "style_name": str(payload.get("style_name", "")),
        "planner_prompts": dict(payload.get("planner_prompts", {})),
        "workflow_inputs": dict(payload.get("workflow_inputs", {})),
        "workflow_inputs_preview": dict(payload.get("workflow_inputs_preview", {})),
        "render_inputs": dict(payload.get("render_inputs", {})),
        "audio_plan": dict(payload.get("audio_plan", {})),
        "audio_map": dict(payload.get("audio_map", {})),
        "style_bible": dict(payload.get("style_bible", {})),
        "shot_plan": list(payload.get("shot_plan", [])),
        "render_plan": list(payload.get("render_plan", [])),
        "still_results": list(payload.get("still_results", [])),
        "clip_results": list(payload.get("clip_results", [])),
        "review_report": dict(payload.get("review_report", {})),
        "final_video": str(payload.get("final_video", "")),
        "music_file": str(payload.get("music_file", "")),
    }
    write_json(run_file(state["run_id"], "manifest.json", scope), out)
    write_json(latest_file("manifest.json", scope), out)
    if str(state.get("status", "")) == "done":
        write_json(latest_success_file("manifest.json", scope), out)
