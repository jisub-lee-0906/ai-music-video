import pytest

from ai_mv.core.contracts.errors import StageFailure
from ai_mv.core.orchestration.input_gate import validate_stage_input


def test_gate_rejects_empty_merge_inputs():
    with pytest.raises(StageFailure):
        validate_stage_input("assemble", {"clip_results": [], "music_file": ""})


def test_gate_accepts_planning_chain():
    validate_stage_input(
        "plan",
        {
            "audio_plan": {"genre_description": "x"},
            "audio_map": {"sections": [{"name": "verse"}]},
            "music_file": "music.mp3",
        },
    )
    validate_stage_input(
        "stills",
        {
            "shot_plan": [{"shot_id": "S001"}],
            "render_plan": [{"shot_id": "S001", "render_mode": "i2v"}],
            "citypop_bible": {"style": "citypop"},
        },
    )


def test_gate_accepts_render_chain():
    validate_stage_input(
        "clips",
        {
            "shot_plan": [{"shot_id": "S001"}],
            "render_plan": [{"shot_id": "S001", "render_mode": "i2v"}],
            "still_results": [{"shot_id": "S001", "image": "stills/S001.png"}],
            "music_file": "music.mp3",
        },
    )
