from __future__ import annotations

from ai_mv.core.contracts.stage_io import StageInput, StageOutput
from ai_mv.core.stages.payload_views import merge_planner_prompt
from ai_mv.engines.seedance_v2_director_plan.planner import build_director_plan_v2, build_director_plan_v2_preview_prompt


def run_director_plan_v2(stage_input: StageInput) -> StageOutput:
    plan = build_director_plan_v2(stage_input.config, stage_input.payload)
    return StageOutput("director_plan_v2", "done", _build_payload(stage_input.payload, plan, stage_input.config), [])


def build_director_plan_v2_preview_payload(config: dict, payload: dict) -> dict:
    plan = build_director_plan_v2(config, payload)
    return _build_payload(payload, plan, config)


def _build_payload(payload: dict, plan: dict, config: dict) -> dict:
    cards = [_card_preview(row) for row in plan.get("shot_packages", [])]
    workflow_v2 = dict(payload.get("workflow_inputs_v2", {}))
    workflow_v2["director_plan_v2"] = {
        "shot_packages": list(plan.get("shot_packages", [])),
        "director_cards": cards,
    }
    return {
        "director_plan_v2": plan,
        "workflow_inputs_v2": workflow_v2,
        "director_cards_preview": cards,
        "planner_prompts": merge_planner_prompt(
            payload,
            "director_plan_v2",
            {"prompt": build_director_plan_v2_preview_prompt(config, payload)},
        ),
    }


def _card_preview(shot: dict) -> dict:
    return {
        "shot_id": str(shot.get("shot_id", "")).strip(),
        "section_label": str(shot.get("section_label", "")).strip(),
        "story_role": str(shot.get("story_role", "")).strip(),
        "visual_role": str(shot.get("visual_role", "")).strip(),
        "zone": str(shot.get("zone", "")).strip(),
        "motif_family": str(shot.get("motif_family", "")).strip(),
        "camera": str(shot.get("camera_intent", "")).strip(),
        "lighting": str(shot.get("lighting_intent", "")).strip(),
        "contact": str(shot.get("contact_intent", "")).strip(),
        "motion": str(shot.get("motion_intent", "")).strip(),
        "continuity_source": str(shot.get("continuity_group", "")).strip(),
        "render_strategy": str(shot.get("render_strategy", "")).strip(),
    }
