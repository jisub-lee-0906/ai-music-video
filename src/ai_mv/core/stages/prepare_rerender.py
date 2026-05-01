from __future__ import annotations

from ai_mv.core.contracts.stage_io import StageInput, StageOutput


_STAGE_SCHEMA = {
    "stills": ("shot_plan", "material_plan", "render_plan", "still_results", "style_bible"),
    "clips": ("shot_plan", "render_plan", "still_results", "music_file"),
    "review": ("final_video", "music_file", "recommended_action", "target_shots", "target_material_ids", "target_section_ids", "assembly_plan", "review_inputs", "sync_repair_summary"),
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

    review_target = stage_inputs.get("review") if isinstance(stage_inputs.get("review"), dict) else None
    if isinstance(review_target, dict):
        if isinstance(stage_input.payload.get("assembly_plan"), dict):
            review_target["assembly_plan"] = _merge_nested_context(review_target.get("assembly_plan"), stage_input.payload.get("assembly_plan"))
        if isinstance(stage_input.payload.get("review_inputs"), dict):
            review_target["review_inputs"] = _merge_nested_context(review_target.get("review_inputs"), stage_input.payload.get("review_inputs"))

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
    if stage_name == "review":
        return {
            "final_video": "",
            "music_file": "",
            "recommended_action": "",
            "target_shots": [],
            "target_material_ids": [],
            "target_section_ids": [],
            "assembly_plan": {},
            "review_inputs": {},
        }
    return {"shot_plan": [], "material_plan": [], "render_plan": [], "still_results": [], "style_bible": {}}



def _merge_stage_field(target: dict[str, object], key: str, value: object) -> None:
    if key in {"music_file", "final_video", "recommended_action"}:
        text = str(value or "").strip()
        if text and not str(target.get(key, "")).strip():
            target[key] = text
        return
    if key == "style_bible":
        if isinstance(value, dict) and not isinstance(target.get(key), dict):
            target[key] = dict(value)
        elif isinstance(value, dict) and not target.get(key):
            target[key] = dict(value)
        return
    if key in {"assembly_plan", "review_inputs", "sync_repair_summary"}:
        if isinstance(value, dict) and not isinstance(target.get(key), dict):
            target[key] = dict(value)
        elif isinstance(value, dict) and not target.get(key):
            target[key] = dict(value)
        return
    if key in {"target_shots", "target_material_ids", "target_section_ids"}:
        if not isinstance(value, list):
            return
        rows = target.setdefault(key, [])
        if not isinstance(rows, list):
            rows = []
            target[key] = rows
        seen = {str(item).strip() for item in rows if str(item).strip()}
        for item in value:
            text = str(item).strip()
            if not text or text in seen:
                continue
            seen.add(text)
            rows.append(text)
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



def _merge_nested_context(existing: object, canonical: object) -> dict[str, object]:
    current = dict(existing) if isinstance(existing, dict) else {}
    source = dict(canonical) if isinstance(canonical, dict) else {}
    merged = dict(current)
    for key, canonical_value in source.items():
        existing_value = merged.get(key)
        if isinstance(existing_value, dict) and isinstance(canonical_value, dict):
            merged[key] = _merge_nested_context(existing_value, canonical_value)
            continue
        if isinstance(existing_value, list) and isinstance(canonical_value, list):
            merged[key] = _merge_context_list(existing_value, canonical_value)
            continue
        merged[key] = canonical_value
    return merged



def _merge_context_list(existing: list, canonical: list) -> list:
    current_map = {_context_item_key(item): item for item in existing}
    canonical_map = {_context_item_key(item): item for item in canonical}
    merged_keys = list(canonical_map.keys()) + [key for key in current_map.keys() if key not in canonical_map]
    merged: list = []
    for key in merged_keys:
        if key in canonical_map and key in current_map and isinstance(current_map[key], dict) and isinstance(canonical_map[key], dict):
            merged.append(_merge_nested_context(current_map[key], canonical_map[key]))
        elif key in canonical_map:
            merged.append(canonical_map[key])
        else:
            merged.append(current_map[key])
    return merged



def _context_item_key(item: object) -> str:
    if isinstance(item, dict):
        for key in ("section_id", "shot_id", "material_id", "id"):
            text = str(item.get(key, "")).strip()
            if text:
                return f"{key}:{text}"
        return repr(sorted(item.items()))
    return str(item)
