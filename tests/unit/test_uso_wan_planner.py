from ai_mv.engines.flux_1_dev_uso.planner import build_uso_plan
from ai_mv.engines.wan_2_2_flf2v.planner import build_wan_plan


def test_uso_planner_double_and_triple():
    payload = {"anchors": [{"shot_id": "a", "anchor": "a.png", "is_chorus": False}, {"shot_id": "b", "anchor": "b.png", "is_chorus": True}]}
    out = build_uso_plan({"consistency": {"reference_images": ["r.png"]}}, payload)
    modes = {x["shot_id"]: x["mode"] for x in out["items"]}
    assert modes["a"] == "double"
    assert modes["b"] == "triple"


def test_wan_planner_splits_triple():
    payload = {"uso_images": [{"shot_id": "x", "keyframe_mode": "triple", "start": "s.png", "mid": "m.png", "end": "e.png", "duration_sec": 6.0}]}
    out = build_wan_plan({"video": {"target": "1920x1080@24"}}, payload)
    assert len(out["clips"]) == 2
    assert out["clips"][0]["shot_id"].endswith("__a")
