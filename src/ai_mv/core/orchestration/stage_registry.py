from __future__ import annotations

from ai_mv.core.stages.acestep_music import run_acestep_music
from ai_mv.core.stages.flux2_ref_chain import run_flux2_ref_chain
from ai_mv.core.stages.lyrics_timeline import run_lyrics_timeline
from ai_mv.core.stages.merge_mux import run_merge_mux
from ai_mv.core.stages.shot_timeline import run_shot_timeline
from ai_mv.core.stages.shot_router import run_shot_router
from ai_mv.core.stages.visual_story_bible import run_visual_story_bible
from ai_mv.core.stages.wan_interpolation import run_wan_interpolation


def ordered_stages() -> list[tuple[str, callable]]:
    return [
        ("acestep_music", run_acestep_music),
        ("lyrics_timeline", run_lyrics_timeline),
        ("visual_story_bible", run_visual_story_bible),
        ("shot_timeline", run_shot_timeline),
        ("shot_router", run_shot_router),
        ("flux2_ref_chain", run_flux2_ref_chain),
        ("wan_interpolation", run_wan_interpolation),
        ("merge_mux", run_merge_mux),
    ]
