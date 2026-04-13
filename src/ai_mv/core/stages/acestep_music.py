from __future__ import annotations

from ai_mv.core.contracts.stage_io import StageInput, StageOutput
from ai_mv.core.stages.payload_views import build_stage_payload
from ai_mv.engines.acestep_1_5_aio.mapper import AUDIO_TEXT, map_audio_workflow
from ai_mv.engines.acestep_1_5_aio.planner import build_audio_plan, build_audio_preview_prompt
from ai_mv.engines.acestep_1_5_aio.runner import run_audio_split


def run_acestep_music(stage_input: StageInput) -> StageOutput:
    payload = dict(stage_input.payload)
    payload["run_id"] = stage_input.run_id
    plan = build_audio_plan(stage_input.config, payload)
    audio_map = run_audio_split(stage_input.config, plan)
    audio_map.update(_audio_context(stage_input.config, audio_map, plan))
    music_file = str(audio_map["music_file"])
    return StageOutput(
        "acestep_music",
        "done",
        build_stage_payload(
            stage_input.payload,
            planner_key="audio",
            planner_value={"prompt": build_audio_preview_prompt(plan)},
            workflow_key="audio",
            workflow_value=_audio_preview_inputs(stage_input.config, plan),
            audio_plan=dict(plan),
            audio_map=audio_map,
            music_file=music_file,
        ),
        [],
    )


def _audio_context(config: dict, audio_map: dict, plan: dict) -> dict:
    return {
        "genre_description": str(plan.get("genre_description", "")).strip(),
        "lyrics": str(plan.get("lyrics", "")).strip(),
        "tags": str(plan.get("tags", "")).strip(),
        "language": str(plan.get("language", "")).strip(),
        "audio_direction": str(plan.get("audio_direction", "")).strip(),
        "hook_direction": str(plan.get("hook_direction", "")).strip(),
        "negative_direction": str(plan.get("negative_direction", "")).strip(),
    }


def _audio_text_inputs(config: dict, plan: dict) -> dict:
    wf = map_audio_workflow(config, plan)
    return dict(wf["node.inputs"][AUDIO_TEXT])


def _audio_preview_inputs(config: dict, plan: dict) -> dict:
    text_inputs = _audio_text_inputs(config, plan)
    return {
        "planner_seed": int(plan.get("seed", 0) or 0),
        "workflow_seed": int(text_inputs.get("seed", 0) or 0),
        "text_inputs": text_inputs,
    }


def build_audio_preview_payload(config: dict, payload: dict, run_id: str) -> dict:
    plan = build_audio_plan(config, dict(payload, run_id=run_id))
    audio_map = build_audio_preview_map(plan)
    audio_map.update(_audio_context(config, audio_map, plan))
    return build_stage_payload(
        payload,
        planner_key="audio",
        planner_value={"prompt": build_audio_preview_prompt(plan)},
        workflow_key="audio",
        workflow_value=_audio_preview_inputs(config, plan),
        audio_plan=dict(plan),
        audio_map=audio_map,
        music_file="",
    )


def build_audio_preview_map(plan: dict) -> dict:
    from ai_mv.engines.acestep_1_5_aio.policy import build_song_timing

    duration = float(plan["duration"])
    timing_bundle = build_song_timing(
        duration,
        plan.get("lyrics_blocks", []),
        int(plan.get("bpm", 0)),
        int(plan.get("beats_per_bar", 4)),
        plan.get("section_bars", {}),
    )
    return {
        "duration_sec": duration,
        "bpm_estimate": int(timing_bundle["timing"]["detected_bpm"]),
        "sections": timing_bundle["sections"],
        "timing": timing_bundle["timing"],
        "music_file": "",
    }
