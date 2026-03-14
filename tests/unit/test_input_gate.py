import pytest

from ai_mv.core.contracts.errors import StageFailure
from ai_mv.core.orchestration.input_gate import validate_stage_input


def test_gate_requires_anchors_for_shot_router():
    with pytest.raises(StageFailure):
        validate_stage_input("shot_router", {})


def test_gate_requires_visual_brief_for_tti():
    with pytest.raises(StageFailure):
        validate_stage_input("tti_anchor", {"audio_map": {"sections": [1]}})


def test_gate_wan_no_longer_requires_flux2_ref_images():
    validate_stage_input(
        "wan_interpolation",
        {
            "clip_routes": [{"shot_id": "x"}],
            "audio_map": {"sections": [{"name": "verse"}]},
            "visual_brief": {"section_briefs": [{"section_name": "verse"}]},
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
