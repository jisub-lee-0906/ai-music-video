from __future__ import annotations

from ai_mv.core.contracts.stage_io import StageInput
from ai_mv.core.stages.acestep_music import build_audio_preview_payload
from ai_mv.core.stages.flux2_ref_chain import build_flux2_ref_preview_payload
from ai_mv.core.stages.shot_router import build_shot_router_preview_payload
from ai_mv.core.stages.shot_timeline import build_shot_timeline_preview_payload
from ai_mv.core.stages.wan_interpolation import build_wan_preview_payload
from ai_mv.engines.lyrics_timeline.planner import build_lyrics_timeline
from ai_mv.engines.lyrics_timeline.planner import build_lyrics_timeline_preview_prompt
from ai_mv.engines.visual_story_bible.planner import build_visual_story_bible
from ai_mv.engines.visual_story_bible.planner import build_visual_story_bible_preview_prompt


def add_audio(stage_input: StageInput) -> None:
    stage_input.payload.update(build_audio_preview_payload(stage_input.config, stage_input.payload, stage_input.run_id))


def add_lyrics_timeline(stage_input: StageInput) -> None:
    timeline = build_lyrics_timeline(stage_input.config, stage_input.payload)
    stage_input.payload.update(
        {
            "lyrics_timeline": timeline,
            "render_inputs": dict(stage_input.payload.get("render_inputs", {}), lyrics_timeline=timeline),
            "planner_prompts": merge_preview(stage_input.payload, "lyrics_timeline", {"prompt": build_lyrics_timeline_preview_prompt(stage_input.payload["audio_plan"], stage_input.payload["audio_map"]["sections"])}),
            "workflow_inputs_preview": merge_preview(stage_input.payload, "lyrics_timeline", {"sections": list(timeline.get("sections", []))}),
        }
    )


def add_story_bible(stage_input: StageInput) -> None:
    story_bible = build_visual_story_bible(stage_input.config, stage_input.payload)
    stage_input.payload.update(
        {
            "visual_story_bible": story_bible,
            "render_inputs": dict(stage_input.payload.get("render_inputs", {}), visual_story_bible=story_bible),
            "planner_prompts": merge_preview(stage_input.payload, "visual_story_bible", {"prompt": build_visual_story_bible_preview_prompt(stage_input.config, stage_input.payload)}),
            "workflow_inputs_preview": merge_preview(stage_input.payload, "visual_story_bible", {"story_bible_preview": story_bible}),
        }
    )


def add_shot_timeline(stage_input: StageInput) -> None:
    stage_input.payload.update(build_shot_timeline_preview_payload(stage_input.config, stage_input.payload))


def add_shot_router(stage_input: StageInput) -> None:
    stage_input.payload.update(build_shot_router_preview_payload(stage_input.config, stage_input.payload))


def add_flux2_ref(stage_input: StageInput) -> None:
    stage_input.payload.update(build_flux2_ref_preview_payload(stage_input.config, stage_input.payload))


def add_wan(stage_input: StageInput) -> None:
    stage_input.payload.update(build_wan_preview_payload(stage_input.config, stage_input.payload))


def merge_preview(payload: dict, key: str, value: dict) -> dict:
    if key in {"audio", "lyrics_timeline", "visual_story_bible", "shot_timeline", "shot_router", "flux2_ref_chain", "wan_interpolation"}:
        root = "planner_prompts" if "prompt" in value or "batches" in value else "workflow_inputs_preview"
        out = dict(payload.get(root, {}))
        out[key] = value
        return out
    raise RuntimeError(f"unsupported preview key: {key}")
