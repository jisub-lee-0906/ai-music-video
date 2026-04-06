import pytest

from ai_mv.core.contracts.errors import StageFailure
from ai_mv.core.orchestration.input_gate import validate_stage_input


def test_gate_rejects_empty_merge_inputs():
    with pytest.raises(StageFailure):
        validate_stage_input("merge_mux", {"clips": [], "music_file": ""})


def test_gate_accepts_planning_chain():
    validate_stage_input(
        "storyboard",
        {
            "audio_plan": {"genre_description": "x"},
            "audio_map": {"sections": [{"name": "verse"}]},
        },
    )
    validate_stage_input("keyframes", {"prompt_plan": {"ref_items": [{"shot_id": "b1"}]}})


def test_gate_accepts_render_chain():
    validate_stage_input(
        "clips",
        {
            "prompt_plan": {"wan_items": [{"shot_id": "b2"}]},
            "flux2_ref_images": [{"shot_id": "b1", "end": "b.png"}],
            "clip_routes": [{"shot_id": "b2", "anchor": "a.png", "duration_sec": 2.0}],
        },
    )
