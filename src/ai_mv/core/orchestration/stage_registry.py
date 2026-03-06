from __future__ import annotations

from ai_mv.core.stages.acestep_music import run_acestep_music
from ai_mv.core.stages.merge_mux import run_merge_mux
from ai_mv.core.stages.tti_anchor import run_tti_anchor
from ai_mv.core.stages.uso_chain import run_uso_chain
from ai_mv.core.stages.visual_bridge import run_visual_bridge
from ai_mv.core.stages.wan_interpolation import run_wan_interpolation


def ordered_stages() -> list[tuple[str, callable]]:
    return [
        ("acestep_music", run_acestep_music),
        ("visual_bridge", run_visual_bridge),
        ("tti_anchor", run_tti_anchor),
        ("uso_chain", run_uso_chain),
        ("wan_interpolation", run_wan_interpolation),
        ("merge_mux", run_merge_mux),
    ]
