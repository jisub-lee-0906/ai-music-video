from __future__ import annotations

from ai_mv.core.contracts.stage_io import StageInput, StageOutput
from ai_mv.core.stages.payload_views import build_stage_payload
from ai_mv.engines.wan_2_2_flf2v.mapper import WAN_TEXT_NEG, WAN_TEXT_POS, map_wan_workflow
from ai_mv.engines.wan_2_2_flf2v.planner import _planner_prompt, _wan_planner_batch_size, build_wan_plan
from ai_mv.engines.wan_2_2_flf2v.runner import run_wan


def run_wan_interpolation(stage_input: StageInput) -> StageOutput:
    plan = build_wan_plan(stage_input.config, stage_input.payload)
    clips = run_wan(stage_input.config, plan)
    return StageOutput(
        "wan_interpolation",
        "done",
        build_stage_payload(
            stage_input.payload,
            planner_key="wan_interpolation",
            planner_value={"batches": _wan_prompt_batches(stage_input, plan)},
            workflow_key="wan_interpolation",
            workflow_value={"clips": _wan_workflow_inputs(stage_input.config, plan["clips"])},
            render_updates={"clips": clips},
            clips=clips,
        ),
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
        if chunk:
            last = chunk[-1]
            carry = " | ".join(
                part
                for part in (
                    str(last.get("subject_motion", "")).strip(),
                    str(last.get("camera_relation", "")).strip(),
                    str(last.get("environment_detail", "")).strip(),
                )
                if part
            )[:120]
    return batches


def _wan_workflow_inputs(config: dict, clips: list[dict]) -> list[dict]:
    out: list[dict] = []
    wan_size = str(config["render"]["wan_size"])
    for clip in clips:
        payload = dict(clip)
        payload["wan_size"] = wan_size
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
                "use_ref": bool(clip.get("use_ref", False)),
                "route_reason": str(clip.get("route_reason", "")),
                "atoms": _wan_atom_view(clip),
            }
        )
    return out


def _wan_atom_view(clip: dict) -> dict:
    return {
        "subject_motion": str(clip.get("subject_motion", "")),
        "camera_relation": str(clip.get("camera_relation", "")),
        "environment_detail": str(clip.get("environment_detail", "")),
    }


def build_wan_preview_payload(config: dict, payload: dict) -> dict:
    plan = build_wan_plan(config, payload)
    stage_input = StageInput(run_id="preflight", config=config, payload=payload)
    return build_stage_payload(
        payload,
        planner_key="wan_interpolation",
        planner_value={"batches": _wan_prompt_batches(stage_input, plan)},
        workflow_key="wan_interpolation",
        workflow_value={"clips": _wan_workflow_inputs(config, plan["clips"])},
        render_updates={"clips": list(plan["clips"])},
        clips=list(plan["clips"]),
    )

