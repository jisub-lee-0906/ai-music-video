import pytest

from ai_mv.core.contracts.errors import StageFailure
from ai_mv.core.orchestration.input_gate import validate_stage_input


def test_gate_requires_anchors_for_shot_router():
    with pytest.raises(StageFailure):
        validate_stage_input("shot_router", {})


def test_gate_requires_story_bible_for_shot_timeline():
    with pytest.raises(StageFailure):
        validate_stage_input("shot_timeline", {"lyrics_timeline": {"sections": [1]}})


def test_gate_wan_requires_new_story_payload_but_not_flux2_ref_images():
    validate_stage_input(
        "wan_interpolation",
        {
            "clip_routes": [{"shot_id": "x", "anchor": "a.png", "duration_sec": 4.0}],
            "audio_map": {"sections": [{"name": "verse"}]},
            "visual_story_bible": {"lyric_beats": [{"beat_id": "b1"}]},
            "shot_timeline": {"shots": [{"lyric_beat_id": "b1"}]},
        },
    )


def test_gate_accepts_when_required_inputs_present():
    payload = {
        "anchors": [{"shot_id": "a"}],
        "clips": [{"shot_id": "a"}],
        "merge_plan": {"ordered": ["a"]},
        "final_video": "x.mp4",
        "audio_duration_sec": 10.0,
        "final_duration_sec": 10.0,
    }
    validate_stage_input("closeout", payload)


def test_gate_rejects_empty_required_value():
    with pytest.raises(StageFailure):
        validate_stage_input("merge_mux", {"clips": [], "music_file": ""})
