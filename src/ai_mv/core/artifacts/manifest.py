from __future__ import annotations

from ai_mv.core.artifacts.paths import latest_file, latest_success_file, run_file
from ai_mv.utils.json_utils import write_json


def write_manifest(state: dict, payload: dict) -> None:
    scope = str(state.get("scope", "run"))
    out = {
        "run_id": state["run_id"],
        "status": state["status"],
        "failure_reason": state["failure_reason"],
        "selected_brief": str(payload.get("selected_brief", "")),
        "lyrics_timeline": dict(payload.get("lyrics_timeline", {})),
        "scene_outline": dict(payload.get("scene_outline", {})),
        "direction_plan": dict(payload.get("direction_plan", {})),
        "prompt_plan": dict(payload.get("prompt_plan", {})),
        "storyboard": dict(payload.get("storyboard", {})),
        "keyframes": dict(payload.get("keyframes", {})),
        "anchors": _anchor_rows(payload),
        "clip_routes": _route_rows(payload),
        "flux2_ref_images": _flux2_ref_rows(payload),
        "clips": list(payload.get("clips", [])),
        "merge_status": str(payload.get("merge_status", "")),
        "final_video": str(payload.get("final_video", "")),
    }
    write_json(run_file(state["run_id"], "manifest.json", scope), out)
    write_json(latest_file("manifest.json", scope), out)
    if str(state.get("status", "")) == "done":
        write_json(latest_success_file("manifest.json", scope), out)


def _anchor_rows(payload: dict) -> list[dict]:
    out: list[dict] = []
    for row in payload.get("anchors", []):
        if not isinstance(row, dict):
            continue
        out.append(
            {
                "shot_id": str(row.get("shot_id", "")),
                "lyric_beat_id": str(row.get("lyric_beat_id", "")),
                "anchor": str(row.get("anchor", "")),
                "retry": int(row.get("retry", 0)),
                "error_body": str(row.get("error_body", "")),
            }
        )
    return out


def _flux2_ref_rows(payload: dict) -> list[dict]:
    out: list[dict] = []
    for row in payload.get("flux2_ref_images", []):
        if not isinstance(row, dict):
            continue
        out.append(
            {
                "shot_id": str(row.get("shot_id", "")),
                "start": str(row.get("start", "")),
                "end": str(row.get("end", "")),
                "retry": int(row.get("retry", 0)),
                "error_body": str(row.get("error_body", "")),
            }
        )
    return out


def _route_rows(payload: dict) -> list[dict]:
    out: list[dict] = []
    for row in payload.get("clip_routes", []):
        if not isinstance(row, dict):
            continue
        out.append(
            {
                "shot_id": str(row.get("shot_id", "")),
                "lyric_beat_id": str(row.get("lyric_beat_id", "")),
                "use_ref": bool(row.get("use_ref", False)),
                "route_reason": str(row.get("route_reason", "")),
                "mv_function": str(row.get("mv_function", "")),
                "hero_frame_score": int(row.get("hero_frame_score", 0)),
                "consistency_need": str(row.get("consistency_need", "")),
            }
        )
    return out
