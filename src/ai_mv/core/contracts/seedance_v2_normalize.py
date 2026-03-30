from __future__ import annotations

from ai_mv.core.contracts.seedance_v2_schema import (
    VALID_RENDER_STRATEGIES,
    assert_director_plan_v2,
    assert_render_plan_v2,
    assert_scene_plan_v2,
)


def normalize_scene_plan_v2(plan: dict) -> dict:
    normalized = dict(plan)
    normalized["shot_packages"] = [_normalize_scene_shot(dict(row)) for row in plan.get("shot_packages", []) if isinstance(row, dict)]
    assert_scene_plan_v2(normalized)
    return normalized


def normalize_director_plan_v2(plan: dict) -> dict:
    normalized = dict(plan)
    normalized["shot_packages"] = [_normalize_director_shot(dict(row)) for row in plan.get("shot_packages", []) if isinstance(row, dict)]
    assert_director_plan_v2(normalized)
    return normalized


def normalize_render_plan_v2(plan: dict) -> dict:
    normalized = dict(plan)
    normalized["master_anchor"] = dict(plan.get("master_anchor", {}))
    normalized["shot_packages"] = [_normalize_render_shot(dict(row)) for row in plan.get("shot_packages", []) if isinstance(row, dict)]
    normalized["wan_chain"] = [dict(row) for row in plan.get("wan_chain", []) if isinstance(row, dict)]
    assert_render_plan_v2(normalized)
    return normalized


def _normalize_scene_shot(shot: dict) -> dict:
    shot["beat_refs"] = [str(x).strip() for x in shot.get("beat_refs", []) if str(x).strip()]
    shot["line_refs"] = [int(x) for x in shot.get("line_refs", []) if _positive_int(x)]
    for key in ("shot_id", "section_name", "section_label", "story_role", "visual_role", "zone", "motif_family", "continuity_group", "identity_core", "environment_anchor"):
        shot[key] = str(shot.get(key, "")).strip()
    shot.setdefault("camera_intent", "")
    shot.setdefault("performance_intent", "")
    shot.setdefault("lighting_intent", "")
    shot.setdefault("shadow_intent", "")
    shot.setdefault("contact_intent", "")
    shot.setdefault("motion_intent", "")
    shot.setdefault("transition_intent", "")
    shot.setdefault("render_strategy", "ref_pair")
    return shot


def _normalize_director_shot(shot: dict) -> dict:
    shot = _normalize_scene_shot(shot)
    for key in ("camera_intent", "performance_intent", "lighting_intent", "shadow_intent", "contact_intent", "motion_intent", "transition_intent"):
        shot[key] = str(shot.get(key, "")).strip()
    return shot


def _normalize_render_shot(shot: dict) -> dict:
    shot = _normalize_director_shot(shot)
    render_strategy = str(shot.get("render_strategy", "")).strip() or "ref_pair"
    shot["render_strategy"] = render_strategy if render_strategy in VALID_RENDER_STRATEGIES else "ref_pair"
    return shot


def _positive_int(value: object) -> bool:
    try:
        return int(value) > 0
    except Exception:
        return False
