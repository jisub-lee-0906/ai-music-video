from __future__ import annotations

from ai_mv.core.contracts.stage_io import StageInput, StageOutput
from ai_mv.engines.flux2_reference.mapper import FLUX2_REF_TEXT_POS, map_flux2_ref_workflow
from ai_mv.engines.flux2_reference.planner import (
    _planner_prompt,
    _flux2_ref_planner_batch_size,
    build_flux2_ref_plan,
)
from ai_mv.engines.flux2_reference.runner import run_flux2_ref


def run_flux2_ref_chain(stage_input: StageInput) -> StageOutput:
    plan = build_flux2_ref_plan(stage_input.config, stage_input.payload)
    flux2_ref_images = run_flux2_ref(stage_input.config, plan) if plan["items"] else []
    return StageOutput(
        "flux2_ref_chain",
        "done",
        {
            "flux2_ref_images": flux2_ref_images,
            "render_inputs": dict(stage_input.payload.get("render_inputs", {}), flux2_ref_images=flux2_ref_images),
            "planner_prompts": _merge_prompt_preview(
                stage_input.payload,
                "flux2_ref_chain",
                {"batches": _flux2_ref_prompt_batches(stage_input, plan)},
            ),
            "workflow_inputs_preview": _merge_workflow_preview(
                stage_input.payload,
                "flux2_ref_chain",
                {"items": _flux2_ref_workflow_inputs(stage_input.config, plan["items"])},
            ),
        },
        [],
    )


def _flux2_ref_prompt_batches(stage_input: StageInput, plan: dict) -> list[dict]:
    anchors = plan["items"]
    if not anchors:
        return []
    batch_size = min(len(anchors), _flux2_ref_planner_batch_size(stage_input.config))
    batches: list[dict] = []
    carry = ""
    for i in range(0, len(anchors), batch_size):
        chunk = anchors[i : i + batch_size]
        prompt = _planner_prompt(stage_input.config, stage_input.payload, chunk, carry)
        batches.append({"index": len(batches) + 1, "shot_ids": [x["shot_id"] for x in chunk], "prompt": prompt})
        if chunk:
            last = chunk[-1]
            carry = " | ".join(
                part
                for part in (
                    str(last.get("subject_clause", "")).strip(),
                    str(last.get("action_clause", "")).strip(),
                    str(last.get("continuity_clause", "")).strip(),
                )
                if part
            )[:140]
    return batches


def _flux2_ref_workflow_inputs(config: dict, items: list[dict]) -> list[dict]:
    out: list[dict] = []
    for item in items:
        start = _flux2_ref_text_input(config, item, "start", 0)
        end = _flux2_ref_text_input(config, item, "end", 1)
        out.append(
            {
                "shot_id": str(item["shot_id"]),
                "route_reason": str(item.get("route_reason", "")),
                "space_relation": str(item.get("space_relation", "")),
                "clip_phase": str(item.get("clip_phase", "")),
                "atoms": _flux2_ref_atom_view(item),
                "start_text": start,
                "end_text": end,
            }
        )
    return out


def _flux2_ref_text_input(config: dict, item: dict, frame_name: str, frame_idx: int) -> str:
    payload = dict(item)
    payload["frame_name"] = frame_name
    payload["frame_idx"] = frame_idx
    payload["filename_prefix"] = f"preview/flux2_ref/{item['shot_id']}/{frame_name}"
    wf = map_flux2_ref_workflow(config, payload)
    return str(wf["node.inputs"][FLUX2_REF_TEXT_POS]["text"])


def _merge_prompt_preview(payload: dict, key: str, value: dict) -> dict:
    out = dict(payload.get("planner_prompts", {}))
    out[key] = value
    return out


def _merge_workflow_preview(payload: dict, key: str, value: dict) -> dict:
    out = dict(payload.get("workflow_inputs_preview", {}))
    out[key] = value
    return out


def _flux2_ref_atom_view(item: dict) -> dict:
    return {
        "subject_clause": str(item.get("subject_clause", "")),
        "action_clause": str(item.get("action_clause", "")),
        "environment_clause": str(item.get("environment_clause", "")),
        "continuity_clause": str(item.get("continuity_clause", "")),
    }

