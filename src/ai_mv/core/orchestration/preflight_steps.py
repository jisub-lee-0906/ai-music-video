from __future__ import annotations

from ai_mv.core.contracts.stage_io import StageInput
from ai_mv.core.stages.acestep_music import build_audio_preview_payload
from ai_mv.core.stages.visual_story_bible import build_visual_story_bible_preview_payload
from ai_mv.core.stages.flux2_ref_chain import build_flux2_ref_preview_payload
from ai_mv.core.stages.lyrics_timeline import build_lyrics_timeline_preview_payload
from ai_mv.core.stages.shot_router import build_shot_router_preview_payload
from ai_mv.core.stages.shot_timeline import build_shot_timeline_preview_payload
from ai_mv.core.stages.wan_interpolation import build_wan_preview_payload


def add_audio(stage_input: StageInput) -> None:
    stage_input.payload.update(build_audio_preview_payload(stage_input.config, stage_input.payload, stage_input.run_id))


def add_lyrics_timeline(stage_input: StageInput) -> None:
    stage_input.payload.update(build_lyrics_timeline_preview_payload(stage_input.config, stage_input.payload))


def add_story_bible(stage_input: StageInput) -> None:
    stage_input.payload.update(build_visual_story_bible_preview_payload(stage_input.config, stage_input.payload))


def add_shot_timeline(stage_input: StageInput) -> None:
    stage_input.payload.update(build_shot_timeline_preview_payload(stage_input.config, stage_input.payload))


def add_shot_router(stage_input: StageInput) -> None:
    stage_input.payload.update(build_shot_router_preview_payload(stage_input.config, stage_input.payload))


def add_flux2_ref(stage_input: StageInput) -> None:
    stage_input.payload.update(build_flux2_ref_preview_payload(stage_input.config, stage_input.payload))


def add_wan(stage_input: StageInput) -> None:
    stage_input.payload.update(build_wan_preview_payload(stage_input.config, stage_input.payload))
