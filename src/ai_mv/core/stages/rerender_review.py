from __future__ import annotations

from ai_mv.core.contracts.stage_io import StageInput, StageOutput
from ai_mv.core.stages.review_stage import run_review_stage


_RESULT_KEYS = {
    "still_results": "still_results",
    "clip_results": "clip_results",
}


def run_rerender_review(stage_input: StageInput) -> StageOutput:
    rerender_results = stage_input.payload.get("rerender_results") if isinstance(stage_input.payload.get("rerender_results"), dict) else {}
    merged_payload = dict(stage_input.payload)
    merged_stills = _merge_asset_rows(stage_input.payload.get("still_results"), rerender_results.get("still_results"))
    merged_clips = _merge_asset_rows(stage_input.payload.get("clip_results"), rerender_results.get("clip_results"))
    merged_payload["still_results"] = merged_stills
    merged_payload["clip_results"] = merged_clips
    merged_payload["review_inputs"] = _merged_review_inputs(stage_input.payload.get("review_inputs"), rerender_results.get("review_inputs"))
    rerender_final_video = (
        str(stage_input.payload.get("rerender_final_video", "")).strip()
        or str(stage_input.payload.get("final_video", "")).strip()
        or str(rerender_results.get("final_video", "")).strip()
    )
    if rerender_final_video:
        merged_payload["final_video"] = rerender_final_video
    rerender_music_file = str(stage_input.payload.get("music_file", "")).strip() or str(rerender_results.get("music_file", "")).strip()
    if rerender_music_file:
        merged_payload["music_file"] = rerender_music_file

    review_out = run_review_stage(StageInput(run_id=stage_input.run_id, config=stage_input.config, payload=merged_payload))
    out_payload = {
        "still_results": merged_stills,
        "clip_results": merged_clips,
        "rerender_review_report": dict(review_out.payload.get("review_report", {})),
    }
    if isinstance(merged_payload.get("review_inputs"), dict) and merged_payload.get("review_inputs"):
        out_payload["review_inputs"] = dict(merged_payload["review_inputs"])
    review_action = str(stage_input.payload.get("review_action", "")).strip() or str(rerender_results.get("review_action", "")).strip()
    if review_action:
        out_payload["review_action"] = review_action
    if rerender_final_video:
        out_payload["rerender_final_video"] = rerender_final_video
    return StageOutput(
        "rerender_review",
        "done",
        out_payload,
        list(review_out.artifacts),
    )



def _merge_asset_rows(existing_rows: object, fresh_rows: object) -> list[dict]:
    merged: list[dict] = []
    fresh_map = {
        str(row.get("shot_id", "")).strip(): row
        for row in fresh_rows if isinstance(fresh_rows, list)
        for _ in [0]
        if isinstance(row, dict) and str(row.get("shot_id", "")).strip()
    }
    for row in existing_rows if isinstance(existing_rows, list) else []:
        if not isinstance(row, dict):
            continue
        shot_id = str(row.get("shot_id", "")).strip()
        if shot_id and shot_id in fresh_map:
            continue
        merged.append(row)
    merged.extend(fresh_map.values())
    return merged



def _merged_review_inputs(existing_inputs: object, fresh_inputs: object) -> dict:
    existing = dict(existing_inputs) if isinstance(existing_inputs, dict) else {}
    fresh = dict(fresh_inputs) if isinstance(fresh_inputs, dict) else {}
    merged = dict(existing)
    for key, value in fresh.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = {**merged[key], **value}
        else:
            merged[key] = value
    return merged
