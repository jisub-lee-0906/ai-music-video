from __future__ import annotations

from ai_mv.core.contracts.stage_io import StageInput, StageOutput
from ai_mv.engines.flux_1_dev_uso.mapper import USO_TEXT_POS, map_uso_workflow
from ai_mv.engines.flux_1_dev_uso.planner import (
    _planner_prompt,
    _uso_planner_batch_size,
    build_uso_plan,
)
from ai_mv.engines.flux_1_dev_uso.runner import run_uso


def run_uso_chain(stage_input: StageInput) -> StageOutput:
    plan = build_uso_plan(stage_input.config, stage_input.payload)
    uso_images = run_uso(stage_input.config, plan)
    return StageOutput(
        "uso_chain",
        "done",
        {
            "uso_images": uso_images,
            "planner_prompts": _merge_prompt_preview(
                stage_input.payload,
                "uso_chain",
                {"batches": _uso_prompt_batches(stage_input, plan)},
            ),
            "workflow_inputs_preview": _merge_workflow_preview(
                stage_input.payload,
                "uso_chain",
                {"items": _uso_workflow_inputs(stage_input.config, plan["items"])},
            ),
        },
        [],
    )


def _uso_prompt_batches(stage_input: StageInput, plan: dict) -> list[dict]:
    anchors = plan["items"]
    batch_size = min(len(anchors), _uso_planner_batch_size(stage_input.config))
    batches: list[dict] = []
    carry = ""
    for i in range(0, len(anchors), batch_size):
        chunk = anchors[i : i + batch_size]
        prompt = _planner_prompt(stage_input.config, stage_input.payload, chunk, carry)
        batches.append({"index": len(batches) + 1, "shot_ids": [x["shot_id"] for x in chunk], "prompt": prompt})
        carry = str(chunk[-1].get("prompt_text", "")).strip()[:220] if chunk else carry
    return batches


def _uso_workflow_inputs(config: dict, items: list[dict]) -> list[dict]:
    out: list[dict] = []
    for item in items:
        start = _uso_text_input(config, item, "start", 0)
        end = _uso_text_input(config, item, "end", 1)
        out.append(
            {
                "shot_id": str(item["shot_id"]),
                "space_relation": str(item.get("space_relation", "")),
                "start_text": start,
                "end_text": end,
            }
        )
    return out


def _uso_text_input(config: dict, item: dict, frame_name: str, frame_idx: int) -> str:
    payload = dict(item)
    payload["frame_name"] = frame_name
    payload["frame_idx"] = frame_idx
    payload["filename_prefix"] = f"preview/uso/{item['shot_id']}/{frame_name}"
    wf = map_uso_workflow(config, payload)
    return str(wf["node.inputs"][USO_TEXT_POS]["text"])


def _merge_prompt_preview(payload: dict, key: str, value: dict) -> dict:
    out = dict(payload.get("planner_prompts", {}))
    out[key] = value
    return out


def _merge_workflow_preview(payload: dict, key: str, value: dict) -> dict:
    out = dict(payload.get("workflow_inputs_preview", {}))
    out[key] = value
    return out

