from __future__ import annotations

from ai_mv.core.contracts.stage_io import StageInput, StageOutput
from ai_mv.engines.flux_2_dev_tti.mapper import TTI_TEXT, map_tti_workflow
from ai_mv.engines.flux_2_dev_tti.planner import build_tti_plan, build_tti_preview_prompt
from ai_mv.engines.flux_2_dev_tti.runner import run_tti


def run_shot_timeline(stage_input: StageInput) -> StageOutput:
    plan = build_tti_plan(stage_input.config, stage_input.payload)
    anchors = run_tti(stage_input.config, plan)
    return StageOutput(
        "shot_timeline",
        "done",
        {
            "anchors": anchors,
            "shot_timeline": {"master_anchor": dict(plan["master_anchor"]), "shots": list(plan["shots"])},
            "render_inputs": dict(stage_input.payload.get("render_inputs", {}), shot_timeline={"master_anchor": dict(plan["master_anchor"]), "shots": list(plan["shots"])}),
            "planner_prompts": _merge(stage_input.payload, "shot_timeline", {"prompt": build_tti_preview_prompt(stage_input.config, stage_input.payload)}),
            "workflow_inputs_preview": _merge(stage_input.payload, "shot_timeline", {"master_anchor": _tti_workflow_input(stage_input.config, plan["master_anchor"]), "shots": _shot_preview(plan["shots"])}),
        },
        [],
    )


def _tti_workflow_input(config: dict, master: dict) -> dict:
    payload = dict(master)
    payload["filename_prefix"] = "preview/tti"
    wf = map_tti_workflow(config, payload)
    return dict(wf["node.inputs"][TTI_TEXT])


def _shot_preview(shots: list[dict]) -> list[dict]:
    out: list[dict] = []
    for shot in shots:
        out.append(
            {
                "shot_id": str(shot.get("shot_id", "")),
                "lyric_beat_id": str(shot.get("lyric_beat_id", "")),
                "section_label": str(shot.get("section_label", shot.get("section_name", ""))),
                "shot_type": str(shot.get("shot_type", "")),
                "edit_role": str(shot.get("edit_role", "")),
                "continuity_lock": str(shot.get("continuity_lock", "")),
                "clip_count": int(shot.get("clip_count", 1)),
                "face_exposure_level": str(shot.get("face_exposure_level", "")),
                "continuity_priority": str(shot.get("continuity_priority", "")),
                "location_family": str(shot.get("location_family", "")),
                "heroine_visibility": str(shot.get("heroine_visibility", "")),
            }
        )
    return out


def _merge(payload: dict, key: str, value: dict) -> dict:
    root = "planner_prompts" if "prompt" in value or "batches" in value else "workflow_inputs_preview"
    out = dict(payload.get(root, {}))
    out[key] = value
    return out


def build_shot_timeline_preview_payload(config: dict, payload: dict) -> dict:
    from ai_mv.engines.flux_2_dev_tti.runner import _pack_anchor

    plan = build_tti_plan(config, payload)
    anchors = [
        _pack_anchor(
            shot,
            "preflight://anchor/master.png",
        )
        for shot in plan["shots"]
    ]
    return {
        "anchors": anchors,
        "shot_timeline": {"master_anchor": dict(plan["master_anchor"]), "shots": list(plan["shots"])},
        "render_inputs": dict(payload.get("render_inputs", {}), shot_timeline={"master_anchor": dict(plan["master_anchor"]), "shots": list(plan["shots"])}),
        "planner_prompts": _merge(payload, "shot_timeline", {"prompt": build_tti_preview_prompt(config, payload)}),
        "workflow_inputs_preview": _merge(
            payload,
            "shot_timeline",
            {"master_anchor": _tti_workflow_input(config, plan["master_anchor"]), "shots": _shot_preview(plan["shots"])},
        ),
    }
