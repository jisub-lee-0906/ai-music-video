from ai_mv.engines.acestep_1_5_split.runner import _sections
from ai_mv.engines.flux_1_dev_tti.planner import _assign_one_shot_per_section
from ai_mv.engines.flux_1_dev_tti.runner import _pack_anchor
from ai_mv.engines.flux_1_dev_uso.runner import _pack_item


def test_audio_sections_preserve_labels_for_downstream():
    blocks = [
        {"section": "intro", "label": "Intro", "lines": ["a", "b"]},
        {"section": "chorus", "label": "Final Chorus", "lines": ["x", "y", "z", "u", "v", "w", "q"]},
    ]
    sections = _sections(20.0, blocks)
    assert sections[1]["label"] == "Final Chorus"


def test_tti_shots_keep_section_label():
    shots = [
        {
            "shot_id": "temp_1",
            "shot_type": "PERF_WIDE",
            "is_chorus": False,
            "camera_language": "clean frame",
            "pose_delta": "small turn",
            "emotion": "lift",
            "scene_detail": "city glow",
            "motion_hint": "slow push",
        }
    ]
    sections = [{"name": "chorus", "label": "Final Chorus", "start_sec": 0.0, "end_sec": 8.0}]
    out = _assign_one_shot_per_section(shots, sections)
    assert out[0]["section_label"] == "Final Chorus"


def test_runner_chain_preserves_section_label():
    shot = {
        "shot_id": "S001",
        "shot_type": "PERF_WIDE",
        "section_name": "chorus",
        "section_label": "Final Chorus",
        "duration_sec": 8.0,
        "is_chorus": True,
        "camera_language": "clean frame",
        "pose_delta": "small turn",
        "emotion": "lift",
        "scene_detail": "city glow",
        "motion_hint": "slow push",
    }
    anchor = _pack_anchor(shot, "anchor.png")
    item = _pack_item({**anchor, "duration_sec": 4.0}, "start.png", "end.png")
    assert anchor["section_label"] == "Final Chorus"
    assert item["section_label"] == "Final Chorus"
