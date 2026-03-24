from __future__ import annotations

from ai_mv.core.contracts.stage_io import StageInput, StageOutput
from ai_mv.core.stages.payload_views import merge_planner_prompt, merge_workflow_preview
from ai_mv.engines.flux_2_dev_ref.mapper import FLUX2_REF_TEXT_POS, map_flux2_ref_workflow
from ai_mv.engines.flux_2_dev_ref.planner import _planner_prompt, _flux2_ref_planner_batch_size, build_flux2_ref_plan
from ai_mv.engines.flux_2_dev_ref.runner import run_flux2_ref


def run_flux2_ref_chain(stage_input: StageInput) -> StageOutput:
    plan = build_flux2_ref_plan(stage_input.config, stage_input.payload)
    flux2_ref_images = run_flux2_ref(stage_input.config, plan) if plan["items"] else []
    return StageOutput(
        "flux2_ref_chain",
        "done",
        {
            "flux2_ref_images": flux2_ref_images,
            "render_inputs": dict(stage_input.payload.get("render_inputs", {}), flux2_ref_images=flux2_ref_images),
            "planner_prompts": merge_planner_prompt(
                stage_input.payload,
                "flux2_ref_chain",
                {"batches": _flux2_ref_prompt_batches(stage_input, plan)},
            ),
            "workflow_inputs_preview": merge_workflow_preview(
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
                    str(last.get("camera_clause", "")).strip(),
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


def _flux2_ref_atom_view(item: dict) -> dict:
    return {
        "prompt_text": str(item.get("prompt_text", "")),
        "subject_clause": str(item.get("subject_clause", "")),
        "action_clause": str(item.get("action_clause", "")),
        "camera_clause": str(item.get("camera_clause", "")),
        "continuity_clause": str(item.get("continuity_clause", "")),
    }


def build_flux2_ref_preview_payload(config: dict, payload: dict) -> dict:
    plan = build_flux2_ref_plan(config, payload)
    flux2_ref_images = []
    for item in plan["items"]:
        row = dict(item)
        sid = str(item["shot_id"])
        row["start"] = f"preflight://flux2_ref/{sid}_start.png"
        row["end"] = f"preflight://flux2_ref/{sid}_end.png"
        flux2_ref_images.append(row)
    stage_input = StageInput(run_id="preflight", config=config, payload=payload)
    return {
        "flux2_ref_images": flux2_ref_images,
        "render_inputs": dict(payload.get("render_inputs", {}), flux2_ref_images=flux2_ref_images),
        "planner_prompts": merge_planner_prompt(payload, "flux2_ref_chain", {"batches": _flux2_ref_prompt_batches(stage_input, plan)}),
        "workflow_inputs_preview": merge_workflow_preview(payload, "flux2_ref_chain", {"items": _flux2_ref_workflow_inputs(config, plan["items"])}),
    }

