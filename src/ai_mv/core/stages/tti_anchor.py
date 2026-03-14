from __future__ import annotations

from ai_mv.core.contracts.stage_io import StageInput, StageOutput
from ai_mv.engines.flux_1_dev_tti.mapper import TTI_TEXT, map_tti_workflow
from ai_mv.engines.flux_1_dev_tti.planner import _planner_prompt, build_tti_plan
from ai_mv.engines.flux_1_dev_tti.runner import run_tti


def run_tti_anchor(stage_input: StageInput) -> StageOutput:
    plan = build_tti_plan(stage_input.config, stage_input.payload)
    anchors = run_tti(stage_input.config, plan)
    return StageOutput(
        "tti_anchor",
        "done",
        {
            "anchors": anchors,
            "planner_prompts": _merge_prompt_preview(
                stage_input.payload,
                "tti_anchor",
                {"prompt": _tti_prompt(stage_input, plan)},
            ),
            "workflow_inputs_preview": _merge_workflow_preview(
                stage_input.payload,
                "tti_anchor",
                {
                    "master_anchor": _tti_workflow_input(stage_input.config, plan["master_anchor"]),
                    "shots": _tti_shot_preview(plan["shots"]),
                },
            ),
        },
        [],
    )


def _tti_prompt(stage_input: StageInput, plan: dict) -> str:
    return _planner_prompt(
        stage_input.config,
        stage_input.payload["audio_map"],
        stage_input.payload["visual_brief"],
        list(stage_input.payload["audio_map"]["sections"]),
    )


def _tti_workflow_input(config: dict, master: dict) -> dict:
    payload = dict(master)
    payload["filename_prefix"] = "preview/tti"
    wf = map_tti_workflow(config, payload)
    return dict(wf["node.inputs"][TTI_TEXT])


def _merge_prompt_preview(payload: dict, key: str, value: dict) -> dict:
    out = dict(payload.get("planner_prompts", {}))
    out[key] = value
    return out


def _merge_workflow_preview(payload: dict, key: str, value: dict) -> dict:
    out = dict(payload.get("workflow_inputs_preview", {}))
    out[key] = value
    return out


def _tti_shot_preview(shots: list[dict]) -> list[dict]:
    out: list[dict] = []
    for shot in shots:
        out.append(
            {
                "shot_id": str(shot.get("shot_id", "")),
                "section_label": str(shot.get("section_label", shot.get("section_name", ""))),
                "shot_type": str(shot.get("shot_type", "")),
                "mv_function": str(shot.get("mv_function", "")),
                "edit_density": str(shot.get("edit_density", "")),
                "shot_priority": str(shot.get("shot_priority", "")),
                "transition_role": str(shot.get("transition_role", "")),
                "hero_frame_score": int(shot.get("hero_frame_score", 0)),
                "consistency_need": str(shot.get("consistency_need", "")),
                "return_weight": int(shot.get("return_weight", 0)),
            }
        )
    return out

