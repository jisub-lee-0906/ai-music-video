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

    _merge_coverage_repair_stage_inputs(stage_input.payload, stage_inputs, target_ids)

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


def _merge_coverage_repair_stage_inputs(payload: dict, stage_inputs: dict[str, dict[str, object]], target_ids: list[str]) -> None:
    assembly_plan = payload.get("assembly_plan") if isinstance(payload.get("assembly_plan"), dict) else {}
    repair_plan = assembly_plan.get("coverage_repair_plan") if isinstance(assembly_plan.get("coverage_repair_plan"), dict) else {}
    if str(repair_plan.get("status", "")).strip() != "repair_required":
        return
    repair_shots = [row for row in repair_plan.get("repair_shots", []) if isinstance(row, dict)] if isinstance(repair_plan.get("repair_shots"), list) else []
    if not repair_shots:
        return
    stills = stage_inputs.setdefault("stills", _empty_stage_payload("stills"))
    clips = stage_inputs.setdefault("clips", _empty_stage_payload("clips"))
    style_bible = payload.get("style_bible") if isinstance(payload.get("style_bible"), dict) else {}
    if style_bible:
        _merge_stage_field(stills, "style_bible", style_bible)
    music_file = str(payload.get("music_file", "")).strip()
    if music_file:
        _merge_stage_field(clips, "music_file", music_file)
    for index, repair_shot in enumerate(repair_shots, start=1):
        shot_id = str(repair_shot.get("shot_id", "")).strip()
        if not shot_id:
            continue
        if shot_id not in target_ids:
            target_ids.append(shot_id)
        material_id = f"COV_REPAIR_MAT_{index:03d}"
        section_id = str(repair_shot.get("section_id", "")).strip()
        target_duration = _safe_float(repair_shot.get("target_duration_sec"), 0.0)
        after_shot_id = str(repair_shot.get("after_shot_id", "")).strip()
        before_shot_id = str(repair_shot.get("before_shot_id", "")).strip()
        render_mode = str(repair_shot.get("render_mode", "ia2v")).strip() or "ia2v"
        repair_type = str(repair_shot.get("repair_type", "coverage_extension_shot")).strip() or "coverage_extension_shot"
        reason_codes = [str(value).strip() for value in repair_shot.get("reason_codes", []) if str(value).strip()] if isinstance(repair_shot.get("reason_codes"), list) else []
        shot_row = {
            "shot_id": shot_id,
            "section_id": section_id,
            "material_id": material_id,
            "render_mode": render_mode,
            "duration_sec": target_duration,
            "source": "assembly_coverage_repair",
            "after_shot_id": after_shot_id,
            "before_shot_id": before_shot_id,
        }
        material_row = {
            "material_id": material_id,
            "section_id": section_id,
            "source": "assembly_coverage_repair",
            "repair_type": repair_type,
        }
        render_row = {
            "shot_id": shot_id,
            "section_id": section_id,
            "material_id": material_id,
            "render_mode": render_mode,
            "source": "assembly_coverage_repair",
            "repair_type": repair_type,
            "reference_mode": "selected_pose_anchor",
            "target_clip_sec": target_duration,
            "edit_intent": {
                "target_clip_sec": target_duration,
                "edit_priority": "high",
                "section_emphasis": "coverage_repair",
                "transition_in": "coverage_handoff_in",
                "transition_out": "coverage_handoff_out",
            },
            "prompt_seed": _coverage_repair_prompt_seed(repair_type, after_shot_id, before_shot_id),
            "clip_prompt_seed": _coverage_repair_clip_prompt_seed(repair_type, after_shot_id, before_shot_id),
            "coverage_repair": {
                "after_shot_id": after_shot_id,
                "before_shot_id": before_shot_id,
                "reason_codes": reason_codes,
            },
        }
        _merge_stage_field(stills, "shot_plan", [shot_row])
        _merge_stage_field(stills, "material_plan", [material_row])
        _merge_stage_field(stills, "render_plan", [render_row])
        _merge_stage_field(clips, "shot_plan", [shot_row])
        _merge_stage_field(clips, "render_plan", [render_row])


def _coverage_repair_prompt_seed(repair_type: str, after_shot_id: str, before_shot_id: str) -> str:
    if repair_type == "coverage_bridge_shot" and after_shot_id and before_shot_id:
        return f"coverage bridge shot between {after_shot_id} and {before_shot_id}; preserve story continuity without introducing a second person"
    if after_shot_id:
        return f"coverage extension shot after {after_shot_id}; preserve story continuity without introducing a second person"
    return "coverage extension shot; preserve story continuity without introducing a second person"


def _coverage_repair_clip_prompt_seed(repair_type: str, after_shot_id: str, before_shot_id: str) -> str:
    if repair_type == "coverage_bridge_shot" and after_shot_id and before_shot_id:
        return f"coverage bridge motion between {after_shot_id} and {before_shot_id}; clean single-subject motion, no clone, no duplicate body"
    if after_shot_id:
        return f"coverage extension motion after {after_shot_id}; clean single-subject motion, no clone, no duplicate body"
    return "coverage extension motion; clean single-subject motion, no clone, no duplicate body"


def _safe_float(value: object, default: float) -> float:
    try:
        return round(float(value), 3)
    except Exception:
        return default


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
