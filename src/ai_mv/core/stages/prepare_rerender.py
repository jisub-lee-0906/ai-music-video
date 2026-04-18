from __future__ import annotations

from ai_mv.core.contracts.stage_io import StageInput, StageOutput


_STAGE_SCHEMA = {
    "stills": ("shot_plan", "render_plan", "still_results"),
    "clips": ("shot_plan", "render_plan", "still_results", "music_file"),
}


def run_prepare_rerender(stage_input: StageInput) -> StageOutput:
    review_report = stage_input.payload.get("review_report")
    execution_payloads = review_report.get("rerender_execution_payloads", []) if isinstance(review_report, dict) else []
    stage_inputs: dict[str, dict[str, object]] = {}
    target_ids: list[str] = []

    for item in execution_payloads if isinstance(execution_payloads, list) else []:
        if not isinstance(item, dict):
            continue
        shot_id = str(item.get("shot_id", "")).strip()
        if shot_id:
            target_ids.append(shot_id)
        payloads = item.get("stage_payloads") if isinstance(item.get("stage_payloads"), dict) else {}
        for stage_name, required_keys in _STAGE_SCHEMA.items():
            stage_patch = payloads.get(stage_name)
            if not isinstance(stage_patch, dict):
                continue
            target = stage_inputs.setdefault(stage_name, _empty_stage_payload(stage_name))
            for key in required_keys:
                _merge_stage_field(target, key, stage_patch.get(key))

    return StageOutput(
        "prepare_rerender",
        "done",
        {
            "rerender_target_ids": target_ids,
            "rerender_stage_sequence": list(stage_inputs.keys()),
            "rerender_stage_inputs": stage_inputs,
        },
        [],
    )



def _empty_stage_payload(stage_name: str) -> dict[str, object]:
    if stage_name == "clips":
        return {"shot_plan": [], "render_plan": [], "still_results": [], "music_file": ""}
    return {"shot_plan": [], "render_plan": [], "still_results": []}



def _merge_stage_field(target: dict[str, object], key: str, value: object) -> None:
    if key == "music_file":
        text = str(value or "").strip()
        if text and not str(target.get("music_file", "")).strip():
            target["music_file"] = text
        return
    if not isinstance(value, list):
        return
    seen = {str(row.get("shot_id", "")).strip() for row in target.get(key, []) if isinstance(row, dict)}
    rows = target.setdefault(key, [])
    if not isinstance(rows, list):
        rows = []
        target[key] = rows
    for row in value:
        if not isinstance(row, dict):
            continue
        shot_id = str(row.get("shot_id", "")).strip()
        dedupe_key = shot_id or repr(sorted(row.items()))
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        rows.append(row)
