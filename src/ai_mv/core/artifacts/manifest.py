from __future__ import annotations

from ai_mv.utils.json_utils import write_json


def write_manifest(state: dict, payload: dict) -> None:
    out = {
        "run_id": state["run_id"],
        "status": state["status"],
        "failure_reason": state["failure_reason"],
        "anchors": _anchor_rows(payload),
        "uso_images": _uso_rows(payload),
        "clips": payload["clips"],
        "merge_status": payload["merge_status"],
        "final_video": payload["final_video"],
    }
    write_json(f"artifacts/runs_state/{state['run_id']}/manifest.json", out)


def _anchor_rows(payload: dict) -> list[dict]:
    out: list[dict] = []
    for row in payload["anchors"]:
        out.append(
            {
                "shot_id": row["shot_id"],
                "anchor_selected": row["anchor_selected"],
                "anchor_candidates": row["anchor_candidates"],
                "retry": row["retry"],
                "error_body": row["error_body"],
            }
        )
    return out


def _uso_rows(payload: dict) -> list[dict]:
    out: list[dict] = []
    for row in payload["uso_images"]:
        mode = row["keyframe_mode"]
        mid = row["mid"] if mode == "triple" else ""
        out.append(
            {
                "shot_id": row["shot_id"],
                "keyframe_mode": mode,
                "start": row["start"],
                "mid": mid,
                "end": row["end"],
                "retry": row["retry"],
                "error_body": row["error_body"],
            }
        )
    return out
