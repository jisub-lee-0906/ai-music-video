from __future__ import annotations

from ai_mv.core.contracts.stage_io import StageInput, StageOutput
from ai_mv.engines.acestep_1_5_split.mapper import AUDIO_TEXT, map_audio_workflow
from ai_mv.engines.acestep_1_5_split.planner import _audio_prompt, build_audio_plan
from ai_mv.engines.acestep_1_5_split.runner import run_audio_split


def run_acestep_music(stage_input: StageInput) -> StageOutput:
    payload = dict(stage_input.payload)
    payload["run_id"] = stage_input.run_id
    plan = build_audio_plan(stage_input.config, payload)
    audio_map = run_audio_split(stage_input.config, plan)
    audio_map.update(_audio_context(plan))
    music_file = str(audio_map["music_file"])
    return StageOutput(
        "acestep_music",
        "done",
        {
            "audio_map": audio_map,
            "music_file": music_file,
            "selected_profile": str(stage_input.config.get("profile", "")).strip(),
            "planner_prompts": _merge_prompt_preview(
                stage_input.payload,
                "audio",
                {"prompt": _audio_prompt(plan)},
            ),
            "workflow_inputs_preview": _merge_workflow_preview(
                stage_input.payload,
                "audio",
                {"text_inputs": _audio_text_inputs(stage_input.config, plan)},
            ),
        },
        [],
    )


def _audio_context(plan: dict) -> dict:
    return {
        "genre_description": str(plan.get("genre_description", "")).strip(),
        "lyrics": str(plan.get("lyrics", "")).strip(),
        "tags": str(plan.get("tags", "")).strip(),
        "style_guidance": str(plan.get("style_guidance", "")).strip(),
        "language": str(plan.get("language", "")).strip(),
        "profile_summary": str(plan.get("profile_summary", "")).strip(),
        "audio_direction": str(plan.get("audio_direction", "")).strip(),
        "hook_direction": str(plan.get("hook_direction", "")).strip(),
        "visual_direction": str(plan.get("visual_direction", "")).strip(),
        "negative_direction": str(plan.get("negative_direction", "")).strip(),
    }


def _merge_prompt_preview(payload: dict, key: str, value: dict) -> dict:
    out = dict(payload.get("planner_prompts", {}))
    out[key] = value
    return out


def _merge_workflow_preview(payload: dict, key: str, value: dict) -> dict:
    out = dict(payload.get("workflow_inputs_preview", {}))
    out[key] = value
    return out


def _audio_text_inputs(config: dict, plan: dict) -> dict:
    wf = map_audio_workflow(config, plan)
    return dict(wf["node.inputs"][AUDIO_TEXT])
