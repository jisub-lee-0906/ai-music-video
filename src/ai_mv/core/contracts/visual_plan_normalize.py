from __future__ import annotations

from ai_mv.core.contracts.visual_plan_schema import (
    assert_direction_plan,
    assert_prompt_plan,
    assert_scene_outline,
)


def normalize_scene_outline(plan: dict) -> dict:
    normalized = dict(plan)
    normalized["shot_packages"] = [_normalize_outline_shot(dict(row)) for row in plan.get("shot_packages", []) if isinstance(row, dict)]
    assert_scene_outline(normalized)
    return normalized


def normalize_direction_plan(plan: dict) -> dict:
    normalized = dict(plan)
    normalized["shot_packages"] = [_normalize_direction_shot(dict(row)) for row in plan.get("shot_packages", []) if isinstance(row, dict)]
    assert_direction_plan(normalized)
    return normalized


def normalize_prompt_plan(plan: dict) -> dict:
    normalized = dict(plan)
    normalized["master_anchor"] = _normalize_master_anchor(dict(plan.get("master_anchor", {})))
    normalized["ref_items"] = [_normalize_prompt_ref_item(dict(row)) for row in plan.get("ref_items", []) if isinstance(row, dict)]
    normalized["wan_items"] = [_normalize_prompt_wan_item(dict(row)) for row in plan.get("wan_items", []) if isinstance(row, dict)]
    assert_prompt_plan(normalized)
    return normalized


def _normalize_outline_shot(shot: dict) -> dict:
    shot["beat_refs"] = [str(x).strip() for x in shot.get("beat_refs", []) if str(x).strip()]
    shot["line_refs"] = [int(x) for x in shot.get("line_refs", []) if _positive_int(x)]
    shot["lyric_lines"] = [str(x).strip() for x in shot.get("lyric_lines", []) if str(x).strip()]
    for key in (
        "shot_id",
        "section_name",
        "section_label",
        "literal_image",
        "visible_action",
        "emotional_turn",
        "continuity_anchor",
        "payoff_role",
        "shot_role",
        "segment_focus",
    ):
        shot[key] = str(shot.get(key, "")).strip()
    shot["duration_sec"] = float(shot.get("duration_sec", 2.0) or 2.0)
    shot["start_beat_index"] = int(shot.get("start_beat_index", 0) or 0)
    shot["end_beat_index"] = int(shot.get("end_beat_index", 0) or 0)
    shot["start_sec"] = float(shot.get("start_sec", 0.0) or 0.0)
    shot["end_sec"] = float(shot.get("end_sec", 0.0) or 0.0)
    shot["anchor_sec"] = float(shot.get("anchor_sec", shot["start_sec"]) or shot["start_sec"])
    return shot


def _normalize_direction_shot(shot: dict) -> dict:
    shot = _normalize_outline_shot(shot)
    for key in ("shot_function", "place", "action", "carry", "framing"):
        shot[key] = str(shot.get(key, "")).strip()
    return shot


def _normalize_prompt_ref_item(row: dict) -> dict:
    row["duration_sec"] = float(row.get("duration_sec", 2.0) or 2.0)
    row["line_refs"] = [int(x) for x in row.get("line_refs", []) if _positive_int(x)]
    row["lyric_lines"] = [str(x).strip() for x in row.get("lyric_lines", []) if str(x).strip()]
    for key in (
        "shot_id",
        "section_name",
        "section_label",
        "literal_image",
        "visible_action",
        "emotional_turn",
        "continuity_anchor",
        "payoff_role",
        "shot_function",
        "place",
        "action",
        "carry",
        "framing",
        "segment_focus",
        "ref_prompt_text",
    ):
        row[key] = str(row.get(key, "")).strip()
    row["start_beat_index"] = int(row.get("start_beat_index", 0) or 0)
    row["end_beat_index"] = int(row.get("end_beat_index", 0) or 0)
    row["start_sec"] = float(row.get("start_sec", 0.0) or 0.0)
    row["end_sec"] = float(row.get("end_sec", 0.0) or 0.0)
    row["anchor_sec"] = float(row.get("anchor_sec", row["start_sec"]) or row["start_sec"])
    return row


def _normalize_prompt_wan_item(row: dict) -> dict:
    row["duration_sec"] = float(row.get("duration_sec", 2.0) or 2.0)
    for key in (
        "shot_id",
        "section_name",
        "section_label",
        "start_ref_shot_id",
        "end_ref_shot_id",
        "place",
        "bridge_action",
        "carry",
        "wan_positive_prompt_text",
    ):
        row[key] = str(row.get(key, "")).strip()
    row["start_anchor_sec"] = float(row.get("start_anchor_sec", 0.0) or 0.0)
    row["end_anchor_sec"] = float(row.get("end_anchor_sec", 0.0) or 0.0)
    return row


def _normalize_master_anchor(row: dict) -> dict:
    for key in ("render_strategy", "identity_core", "style_contract", "environment_anchor"):
        row[key] = str(row.get(key, "")).strip()
    return row


def _positive_int(value: object) -> bool:
    try:
        return int(value) > 0
    except Exception:
        return False
