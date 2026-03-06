from __future__ import annotations

from ai_mv.utils.json_utils import write_json


def write_manifest(state: dict, payload: dict) -> None:
    out = {
        "run_id": state["run_id"],
        "status": state["status"],
        "failure_reason": state["failure_reason"],
        "anchors": _anchor_rows(payload),
        "uso_images": _uso_rows(payload),
        "clips": list(payload.get("clips", [])),
        "merge_status": str(payload.get("merge_status", "")),
        "final_video": str(payload.get("final_video", "")),
    }
    write_json(f"artifacts/runs_state/{state['run_id']}/manifest.json", out)


def _anchor_rows(payload: dict) -> list[dict]:
    out: list[dict] = []
    for row in payload.get("anchors", []):
        if not isinstance(row, dict):
            continue
        out.append(
            {
                "shot_id": str(row.get("shot_id", "")),
                "anchor": str(row.get("anchor", row.get("anchor_selected", ""))),
                "anchor_selected": str(row.get("anchor_selected", row.get("anchor", ""))),
                "retry": int(row.get("retry", 0)),
                "error_body": str(row.get("error_body", "")),
            }
        )
    return out


def _uso_rows(payload: dict) -> list[dict]:
    out: list[dict] = []
    for row in payload.get("uso_images", []):
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
