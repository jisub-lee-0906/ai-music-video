from __future__ import annotations

from ai_mv.core.contracts.stage_io import StageInput, StageOutput
from ai_mv.engines.visual_bridge.planner import _planner_prompt, build_visual_brief


def run_visual_bridge(stage_input: StageInput) -> StageOutput:
    audio_map = stage_input.payload["audio_map"]
    sections = list(audio_map["sections"])
    brief = build_visual_brief(stage_input.config, stage_input.payload)
    return StageOutput(
        "visual_bridge",
        "done",
        {
            "visual_brief": brief,
            "render_inputs": dict(stage_input.payload.get("render_inputs", {}), visual_brief=brief),
            "planner_prompts": _merge_prompt_preview(
                stage_input.payload,
                "visual_bridge",
                {"prompt": _planner_prompt(stage_input.config, audio_map, sections)},
            ),
        },
        [],
    )


def _merge_prompt_preview(payload: dict, key: str, value: dict) -> dict:
    out = dict(payload.get("planner_prompts", {}))
    out[key] = value
    return out
