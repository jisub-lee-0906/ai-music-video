from ai_mv.engines.flux_1_dev_uso.planner import build_uso_plan
from ai_mv.engines.wan_2_2_flf2v.planner import build_wan_plan
import ai_mv.engines.flux_1_dev_uso.planner as uso_planner
import ai_mv.engines.wan_2_2_flf2v.planner as wan_planner


def test_uso_planner_double_and_triple(monkeypatch):
    monkeypatch.setattr(uso_planner, "generate_structured", _fake_uso_generate)
    payload = {"anchors": [_anchor("a", False), _anchor("b", True)]}
    out = build_uso_plan({"style": {"guidance": "g"}}, payload)
    modes = {x["shot_id"]: x["mode"] for x in out["items"]}
    assert modes["a"] == "double"
    assert modes["b"] == "triple"


def test_wan_planner_splits_triple(monkeypatch):
    monkeypatch.setattr(wan_planner, "generate_structured", _fake_wan_generate)
    payload = {"uso_images": [{"shot_id": "x", "keyframe_mode": "triple", "start": "s.png", "mid": "m.png", "end": "e.png", "duration_sec": 6.0}]}
    out = build_wan_plan({"video": {"target": "1920x1080@24"}}, payload)
    assert len(out["clips"]) == 2
    assert out["clips"][0]["shot_id"].endswith("__a")


def _anchor(shot_id: str, chorus: bool) -> dict:
    return {
        "shot_id": shot_id,
        "anchor": f"{shot_id}.png",
        "is_chorus": chorus,
        "duration_sec": 4.0,
        "shot_type": "CHAR_MASTER",
    }


def _fake_uso_generate(_config, _prompt, _schema):
    return {"items": [{"shot_id": "a", "mode": "double", "delta": "d1"}, {"shot_id": "b", "mode": "triple", "delta": "d2"}]}


def _fake_wan_generate(_config, _prompt, _schema):
    return {
        "clips": [
            {"shot_id": "x__a", "prompt": "p1", "negative_prompt": "n1", "energy": "mid"},
            {"shot_id": "x__b", "prompt": "p2", "negative_prompt": "n2", "energy": "mid"},
        ]
    }
