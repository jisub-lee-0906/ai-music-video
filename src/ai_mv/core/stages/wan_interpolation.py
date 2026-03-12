from __future__ import annotations

from ai_mv.core.contracts.stage_io import StageInput, StageOutput
from ai_mv.engines.wan_2_2_flf2v.mapper import WAN_TEXT_NEG, WAN_TEXT_POS, map_wan_workflow
from ai_mv.engines.wan_2_2_flf2v.planner import (
    _planner_prompt,
    _wan_planner_batch_size,
    build_wan_plan,
)
from ai_mv.engines.wan_2_2_flf2v.runner import run_wan


def run_wan_interpolation(stage_input: StageInput) -> StageOutput:
    plan = build_wan_plan(stage_input.config, stage_input.payload)
    clips = run_wan(stage_input.config, plan)
    return StageOutput(
        "wan_interpolation",
        "done",
        {
            "clips": clips,
            "planner_prompts": _merge_prompt_preview(
                stage_input.payload,
                "wan_interpolation",
                {"batches": _wan_prompt_batches(stage_input, plan)},
            ),
            "workflow_inputs_preview": _merge_workflow_preview(
                stage_input.payload,
                "wan_interpolation",
                {"clips": _wan_workflow_inputs(stage_input.config, plan["clips"])},
            ),
        },
        [],
    )


def _wan_prompt_batches(stage_input: StageInput, plan: dict) -> list[dict]:
    clips = plan["clips"]
    batch_size = _wan_planner_batch_size(stage_input.config, len(clips))
    batches: list[dict] = []
    carry = ""
    for i in range(0, len(clips), batch_size):
        chunk = clips[i : i + batch_size]
        prompt = _planner_prompt(stage_input.config, stage_input.payload, chunk, carry)
        batches.append({"index": len(batches) + 1, "shot_ids": [x["shot_id"] for x in chunk], "prompt": prompt})
        carry = str(chunk[-1].get("positive_prompt", "")).strip()[:220] if chunk else carry
    return batches


def _wan_workflow_inputs(config: dict, clips: list[dict]) -> list[dict]:
    out: list[dict] = []
    wan_size = str(config["render"]["wan_size"])
    for clip in clips:
        payload = dict(clip)
        payload["wan_size"] = wan_size
        payload["seed_offset"] = 0
        payload["filename_prefix"] = f"preview/clips/{clip['shot_id']}"
        wf = map_wan_workflow(config, payload)
        inputs = wf["node.inputs"]
        out.append(
            {
                "shot_id": str(clip["shot_id"]),
                "positive_prompt": str(inputs[WAN_TEXT_POS]["text"]),
                "negative_prompt": str(inputs[WAN_TEXT_NEG]["text"]),
                "energy": str(clip.get("energy", "")),
                "space_relation": str(clip.get("space_relation", "")),
            }
        )
    return out


def _merge_prompt_preview(payload: dict, key: str, value: dict) -> dict:
    out = dict(payload.get("planner_prompts", {}))
    out[key] = value
    return out


def _merge_workflow_preview(payload: dict, key: str, value: dict) -> dict:
    out = dict(payload.get("workflow_inputs_preview", {}))
    out[key] = value
    return out

