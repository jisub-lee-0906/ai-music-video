import pytest

from ai_mv.core.contracts.errors import StageFailure
from ai_mv.core.orchestration.input_gate import validate_stage_input


def test_gate_rejects_empty_merge_inputs():
    with pytest.raises(StageFailure):
        validate_stage_input("merge_mux", {"clips": [], "music_file": ""})


def test_gate_accepts_planning_chain():
    validate_stage_input(
        "scene_plan",
        {
            "audio_plan": {"genre_description": "x"},
            "audio_map": {"sections": [{"name": "verse"}]},
            "lyrics_timeline": {"sections": [{"section_name": "Verse 1"}]},
        },
    )
    validate_stage_input("director_plan", {"scene_plan": {"shot_packages": [{"shot_id": "b1"}]}})
    validate_stage_input("render_plan", {"director_plan": {"shot_packages": [{"shot_id": "b1"}]}})
    validate_stage_input("backend_preview", {"render_plan": {"shot_packages": [{"shot_id": "b1"}]}})


def test_gate_accepts_render_chain():
    validate_stage_input("tti_anchor", {"render_plan": {"shot_packages": [{"shot_id": "b1"}]}})
    validate_stage_input(
        "flux2_ref_chain",
        {
            "render_plan": {"shot_packages": [{"shot_id": "b1"}]},
            "master_anchor": "anchors/character_master.png",
        },
    )
    validate_stage_input(
        "wan_interpolation",
        {
            "render_plan": {"wan_chain": [{"shot_id": "b1"}]},
            "flux2_ref_images": [{"shot_id": "b1", "start": "a.png", "end": "b.png"}],
            "clip_routes": [{"shot_id": "b1", "anchor": "a.png", "duration_sec": 2.0}],
        },
    )
