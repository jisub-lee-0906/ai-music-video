from __future__ import annotations


SCENE_OUTLINE_REQUIRED_FIELDS = (
    "shot_id",
    "section_name",
    "section_label",
    "beat_refs",
    "line_refs",
    "story_function",
    "story_goal",
    "world_zone",
    "heroine_state",
    "transition_need",
    "why",
)

DIRECTOR_REQUIRED_FIELDS = (
    *SCENE_OUTLINE_REQUIRED_FIELDS,
    "shot_function",
    "ref_archetype",
    "archetype_variant",
    "primary_surface",
    "dominant_action",
    "continuity_delta",
    "content_trace",
    "identity_hook_policy",
)

PROMPT_REQUIRED_REF_FIELDS = (
    "shot_id",
    "section_name",
    "section_label",
    "duration_sec",
    "ref_archetype",
    "archetype_variant",
    "primary_surface",
    "dominant_action",
    "continuity_delta",
    "content_trace",
    "selected_prompt_shape",
    "applied_grammar_source",
    "why",
    "ref_prompt_atoms",
    "ref_prompt_contract",
    "ref_start_prompt_text",
    "ref_end_prompt_text",
)

PROMPT_REQUIRED_WAN_FIELDS = (
    "shot_id",
    "section_name",
    "section_label",
    "start_ref_shot_id",
    "end_ref_shot_id",
    "duration_sec",
    "wan_transition_family",
    "wan_prompt_contract",
    "wan_positive_prompt_text",
    "why",
)


def assert_scene_outline(plan: dict) -> None:
    if not isinstance(plan.get("shot_packages"), list) or not plan["shot_packages"]:
        raise ValueError("scene_outline.shot_packages must be a non-empty list")
    for shot in plan["shot_packages"]:
        if not isinstance(shot, dict):
            raise ValueError("scene_outline shot_packages must contain objects")
        for key in SCENE_OUTLINE_REQUIRED_FIELDS:
            if key not in shot:
                raise ValueError(f"scene_outline shot missing field: {key}")


def assert_direction_plan(plan: dict) -> None:
    if not isinstance(plan.get("shot_packages"), list) or not plan["shot_packages"]:
        raise ValueError("direction_plan.shot_packages must be a non-empty list")
    for shot in plan["shot_packages"]:
        if not isinstance(shot, dict):
            raise ValueError("direction_plan shot_packages must contain objects")
        for key in DIRECTOR_REQUIRED_FIELDS:
            if key not in shot:
                raise ValueError(f"direction_plan shot missing field: {key}")


def assert_prompt_plan(plan: dict) -> None:
    if not isinstance(plan.get("master_anchor"), dict):
        raise ValueError("prompt_plan.master_anchor must be an object")
    if not isinstance(plan.get("ref_items"), list) or not plan["ref_items"]:
        raise ValueError("prompt_plan.ref_items must be a non-empty list")
    if not isinstance(plan.get("wan_items"), list):
        raise ValueError("prompt_plan.wan_items must be a list")
    for row in plan["ref_items"]:
        if not isinstance(row, dict):
            raise ValueError("prompt_plan.ref_items must contain objects")
        for key in PROMPT_REQUIRED_REF_FIELDS:
            if key not in row:
                raise ValueError(f"prompt_plan ref item missing field: {key}")
    for row in plan["wan_items"]:
        if not isinstance(row, dict):
            raise ValueError("prompt_plan.wan_items must contain objects")
        for key in PROMPT_REQUIRED_WAN_FIELDS:
            if key not in row:
                raise ValueError(f"prompt_plan wan item missing field: {key}")
