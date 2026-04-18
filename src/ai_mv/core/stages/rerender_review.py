from __future__ import annotations

from ai_mv.core.contracts.stage_io import StageInput, StageOutput
from ai_mv.core.stages.review_outputs import run_review_outputs


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

    review_out = run_review_outputs(StageInput(run_id=stage_input.run_id, config=stage_input.config, payload=merged_payload))
    return StageOutput(
        "rerender_review",
        "done",
        {
            "still_results": merged_stills,
            "clip_results": merged_clips,
            "rerender_review_report": dict(review_out.payload.get("review_report", {})),
        },
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
