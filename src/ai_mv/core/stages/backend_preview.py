from __future__ import annotations

from ai_mv.core.contracts.stage_io import StageInput, StageOutput
from ai_mv.core.stages.payload_views import merge_planner_prompt, merge_workflow_preview


def build_backend_preview(config: dict, payload: dict) -> dict:
    prompt_plan = payload.get("prompt_plan", {}) if isinstance(payload, dict) else {}
    ref_items = [row for row in prompt_plan.get("ref_items", []) if isinstance(row, dict)]
    wan_items = [row for row in prompt_plan.get("wan_items", []) if isinstance(row, dict)]
    master_anchor = dict(prompt_plan.get("master_anchor", {})) if isinstance(prompt_plan, dict) else {}
    return {
        "tti_adapter": {
            "master_anchor_contract": master_anchor,
        },
        "ref_adapter": [
            {
                "shot_id": str(row.get("shot_id", "")).strip(),
                "section_name": str(row.get("section_name", "")).strip(),
                "section_label": str(row.get("section_label", "")).strip(),
                "start_prompt_preview": str(row.get("ref_start_prompt_text", "")).strip(),
                "end_prompt_preview": str(row.get("ref_end_prompt_text", "")).strip(),
                "raw_prompt_clauses": {
                    "story_function": str(row.get("story_function", "")).strip(),
                    "story_goal": str(row.get("story_goal", "")).strip(),
                    "world_zone": str(row.get("world_zone", "")).strip(),
                    "shot_function": str(row.get("shot_function", "")).strip(),
                    "ref_archetype": str(row.get("ref_archetype", "")).strip(),
                    "archetype_variant": str(row.get("archetype_variant", "")).strip(),
                    "primary_surface": str(row.get("primary_surface", "")).strip(),
                    "dominant_action": str(row.get("dominant_action", "")).strip(),
                    "continuity_delta": str(row.get("continuity_delta", "")).strip(),
                    "content_trace": str(row.get("content_trace", "")).strip(),
                    "selected_prompt_shape": str(row.get("selected_prompt_shape", "")).strip(),
                    "applied_grammar_source": str(row.get("applied_grammar_source", "")).strip(),
                    "why": str(row.get("why", "")).strip(),
                    "start_state": str(row.get("ref_prompt_atoms", {}).get("start_state", "")).strip(),
                    "end_state": str(row.get("ref_prompt_atoms", {}).get("end_state", "")).strip(),
                },
            }
            for row in ref_items
        ],
        "wan_adapter": [
            {
                "shot_id": str(row.get("shot_id", "")).strip(),
                "section_name": str(row.get("section_name", "")).strip(),
                "section_label": str(row.get("section_label", "")).strip(),
                "positive_prompt_preview": str(row.get("wan_positive_prompt_text", "")).strip(),
                "raw_prompt_clauses": {
                    "story_function": str(row.get("story_function", "")).strip(),
                    "wan_transition_family": str(row.get("wan_transition_family", "")).strip(),
                    "bridge_action": str(row.get("wan_prompt_atoms", {}).get("bridge_action", "")).strip(),
                    "primary_surface": str(row.get("wan_prompt_atoms", {}).get("primary_surface", "")).strip(),
                    "start_ref_shot_id": str(row.get("start_ref_shot_id", "")).strip(),
                    "end_ref_shot_id": str(row.get("end_ref_shot_id", "")).strip(),
                    "applied_grammar_source": str(row.get("applied_grammar_source", "")).strip(),
                    "why": str(row.get("why", "")).strip(),
                },
            }
            for row in wan_items
        ],
    }


def run_backend_preview(stage_input: StageInput) -> StageOutput:
    preview = build_backend_preview(stage_input.config, stage_input.payload)
    return StageOutput(
        "backend_preview",
        "done",
        {
            "backend_preview": preview,
            "workflow_inputs_preview": merge_workflow_preview(stage_input.payload, "backend_preview", preview),
            "planner_prompts": merge_planner_prompt(
                stage_input.payload,
                "backend_preview",
                {"prompt": "Expose scene outline, direction plan, and prompt plan contracts as backend-ready previews."},
            ),
        },
        [],
    )
