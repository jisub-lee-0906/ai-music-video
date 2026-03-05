from ai_mv.engines.flux_1_dev_uso.planner import build_uso_plan
from ai_mv.engines.wan_2_2_flf2v.planner import build_wan_plan
import ai_mv.engines.flux_1_dev_uso.planner as uso_planner
import ai_mv.engines.wan_2_2_flf2v.planner as wan_planner


def test_uso_planner_double(monkeypatch):
    monkeypatch.setattr(uso_planner, "generate_structured", _fake_uso_generate)
    payload = {"anchors": [_anchor("a", False), _anchor("b", True)]}
    out = build_uso_plan({"style": {"guidance": "g"}}, payload)
    shot_ids = [x["shot_id"] for x in out["items"]]
    assert shot_ids == ["a", "b"]
    assert out["items"][0]["prompt_text"]


def test_uso_planner_shot_id_coerce(monkeypatch):
    monkeypatch.setattr(uso_planner, "generate_structured", _fake_uso_generate_mismatch)
    payload = {"anchors": [_anchor("intro_000", False)]}
    out = build_uso_plan({"style": {"guidance": "g"}}, payload)
    assert out["items"][0]["shot_id"] == "intro_000"
    assert "flower" in out["items"][0]["prompt_text"].lower()


def test_wan_planner_uses_start_end_only(monkeypatch):
    monkeypatch.setattr(wan_planner, "generate_structured", _fake_wan_generate)
    payload = {"uso_images": [{"shot_id": "x", "start": "s.png", "end": "e.png", "duration_sec": 6.0}]}
    out = build_wan_plan({"video": {"target": "1920x1080@24"}}, payload)
    assert len(out["clips"]) == 1
    assert out["clips"][0]["shot_id"] == "x"


def _anchor(shot_id: str, chorus: bool) -> dict:
    return {
        "shot_id": shot_id,
        "anchor": f"{shot_id}.png",
        "is_chorus": chorus,
        "duration_sec": 4.0,
        "shot_type": "CHAR_MASTER",
    }


def _fake_uso_generate(_config, _prompt, _schema):
    return {
        "items": [
            {
                "shot_id": "a",
                "delta": "d1",
                "prompt_text": "A European girl smiles warmly in a summer flower field.",
                "negative_prompt": "blurry, deformed face, low detail",
            },
            {
                "shot_id": "b",
                "delta": "d2",
                "prompt_text": "A performer breathes slowly under sunset light with calm expression.",
                "negative_prompt": "artifact, bad anatomy, extra limbs",
            },
        ]
    }


def _fake_uso_generate_mismatch(_config, _prompt, _schema):
    return {
        "items": [
            {
                "shot_id": "intro_001",
                "delta": "small gaze shift",
                "prompt_text": "A European girl with a heartfelt smile stands in an endless blooming flower field under a clear summer sky with warm daylight.",
                "negative_prompt": "low quality, blurry, jpeg artifacts, bad hands",
            }
        ]
    }


def _fake_wan_generate(_config, _prompt, _schema):
    return {
        "clips": [
            {"shot_id": "x", "positive_prompt": "p1", "negative_prompt": "n1", "energy": "normal"},
        ]
    }
