from ai_mv.core.quality.quality_gate import evaluate_quality


def test_quality_deterministic():
    payload = {
        "final_video": "x.mp4",
        "clips": [{"video": "c1.mp4"}],
        "merge_plan": {"ordered": ["c1.mp4"]},
        "audio_duration_sec": 10.0,
        "final_duration_sec": 10.0,
        "anchors": [{"anchor_selected": "a.png"}],
    }
    assert evaluate_quality(payload) == evaluate_quality(payload)
