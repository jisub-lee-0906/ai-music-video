from __future__ import annotations


REQUIRED_SHOT_FIELDS = (
    "shot_id",
    "section_name",
    "section_label",
    "beat_refs",
    "line_refs",
    "story_role",
    "visual_role",
    "zone",
    "motif_family",
    "continuity_group",
    "identity_core",
    "environment_anchor",
    "camera_intent",
    "performance_intent",
    "lighting_intent",
    "shadow_intent",
    "contact_intent",
    "motion_intent",
    "transition_intent",
    "render_strategy",
)

VALID_RENDER_STRATEGIES = {"tti_master", "ref_pair", "wan_chain"}


def assert_v2_shot_package(shot: dict) -> None:
    missing = [key for key in REQUIRED_SHOT_FIELDS if key not in shot]
    if missing:
        raise ValueError(f"v2 shot package missing fields: {', '.join(missing)}")
    if str(shot.get("render_strategy", "")).strip() not in VALID_RENDER_STRATEGIES:
        raise ValueError(f"invalid v2 render_strategy: {shot.get('render_strategy', '')}")
    if not isinstance(shot.get("beat_refs"), list) or not shot["beat_refs"]:
        raise ValueError("v2 shot package beat_refs must be a non-empty list")
    if not isinstance(shot.get("line_refs"), list):
        raise ValueError("v2 shot package line_refs must be a list")


def assert_scene_plan_v2(plan: dict) -> None:
    if not isinstance(plan.get("shot_packages"), list) or not plan["shot_packages"]:
        raise ValueError("scene_plan_v2.shot_packages must be a non-empty list")
    for shot in plan["shot_packages"]:
        if not isinstance(shot, dict):
            raise ValueError("scene_plan_v2 shot_packages must contain objects")
        for key in ("shot_id", "section_name", "section_label", "beat_refs", "line_refs", "story_role", "visual_role", "zone", "motif_family", "continuity_group", "identity_core", "environment_anchor"):
            if key not in shot:
                raise ValueError(f"scene_plan_v2 shot missing field: {key}")


def assert_director_plan_v2(plan: dict) -> None:
    if not isinstance(plan.get("shot_packages"), list) or not plan["shot_packages"]:
        raise ValueError("director_plan_v2.shot_packages must be a non-empty list")
    for shot in plan["shot_packages"]:
        if not isinstance(shot, dict):
            raise ValueError("director_plan_v2 shot_packages must contain objects")
        for key in ("camera_intent", "performance_intent", "lighting_intent", "shadow_intent", "contact_intent", "motion_intent", "transition_intent"):
            if key not in shot:
                raise ValueError(f"director_plan_v2 shot missing intent field: {key}")


def assert_render_plan_v2(plan: dict) -> None:
    if not isinstance(plan.get("master_anchor"), dict):
        raise ValueError("render_plan_v2.master_anchor must be an object")
    if str(plan["master_anchor"].get("render_strategy", "")).strip() != "tti_master":
        raise ValueError("render_plan_v2.master_anchor.render_strategy must be tti_master")
    if not isinstance(plan.get("shot_packages"), list) or not plan["shot_packages"]:
        raise ValueError("render_plan_v2.shot_packages must be a non-empty list")
    if not isinstance(plan.get("wan_chain"), list) or not plan["wan_chain"]:
        raise ValueError("render_plan_v2.wan_chain must be a non-empty list")
    for shot in plan["shot_packages"]:
        assert_v2_shot_package(shot)
