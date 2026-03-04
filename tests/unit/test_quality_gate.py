from ai_mv.core.quality.quality_gate import evaluate_quality


def test_quality_deterministic():
    payload = {"a": 1, "b": "x"}
    assert evaluate_quality(payload) == evaluate_quality(payload)

