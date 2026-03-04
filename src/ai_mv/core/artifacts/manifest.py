from __future__ import annotations

from ai_mv.utils.json_utils import write_json


def write_manifest(state: dict, payload: dict) -> None:
    out = {
        "run_id": state["run_id"],
        "status": state["status"],
        "failure_reason": state.get("failure_reason", ""),
        "anchors": _anchor_rows(payload),
        "uso_images": _uso_rows(payload),
        "clips": payload.get("clips", []),
        "merge_status": payload.get("merge_status", ""),
        "final_video": payload.get("final_video", ""),
    }
    write_json(f"artifacts/runs_state/{state['run_id']}/manifest.json", out)


def _anchor_rows(payload: dict) -> list[dict]:
    out: list[dict] = []
    for row in payload.get("anchors", []):
        out.append(
            {
                "shot_id": row.get("shot_id", ""),
                "anchor_selected": row.get("anchor_selected", row.get("anchor", "")),
                "anchor_candidates": row.get("anchor_candidates", []),
                "retry": row.get("retry", 0),
                "error_body": row.get("error_body", ""),
            }
        )
    return out


def _uso_rows(payload: dict) -> list[dict]:
    out: list[dict] = []
    for row in payload.get("uso_images", []):
        out.append(
            {
                "shot_id": row.get("shot_id", ""),
                "keyframe_mode": row.get("keyframe_mode", "double"),
                "start": row.get("start", ""),
                "mid": row.get("mid", ""),
                "end": row.get("end", ""),
                "retry": row.get("retry", 0),
                "error_body": row.get("error_body", ""),
            }
        )
    return out
