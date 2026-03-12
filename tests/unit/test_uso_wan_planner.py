import pytest

from ai_mv.engines.flux_1_dev_uso.planner import build_uso_plan
from ai_mv.engines.wan_2_2_flf2v.planner import build_wan_plan
import ai_mv.engines.flux_1_dev_uso.planner as uso_planner
import ai_mv.engines.wan_2_2_flf2v.planner as wan_planner


def test_uso_planner_double(monkeypatch):
    monkeypatch.setattr(uso_planner, "generate_structured", _fake_uso_generate)
    payload = {"anchors": [_anchor("a", False), _anchor("b", True)], "audio_map": {"style_guidance": "g"}, "visual_brief": _brief()}
    out = build_uso_plan({}, payload)
    shot_ids = [x["shot_id"] for x in out["items"]]
    assert shot_ids == ["a", "b"]
    assert out["items"][0]["prompt_text"]


def test_uso_planner_allows_missing_style_guidance(monkeypatch):
    monkeypatch.setattr(uso_planner, "generate_structured", _fake_uso_generate)
    payload = {"anchors": [_anchor("a", False)], "visual_brief": _brief()}
    out = build_uso_plan({}, payload)
    assert out["items"][0]["prompt_text"]
    assert "style_guidance" not in out["items"][0]


def test_uso_planner_shot_id_coerce(monkeypatch):
    monkeypatch.setattr(uso_planner, "generate_structured", _fake_uso_generate_mismatch)
    payload = {"anchors": [_anchor("intro_000", False)], "audio_map": {"style_guidance": "g"}, "visual_brief": _brief()}
    out = build_uso_plan({"render": {"strict_prompt_id_match": False}}, payload)
    assert out["items"][0]["shot_id"] == "intro_000"
    assert "flower" in out["items"][0]["prompt_text"].lower()


def test_uso_planner_shot_id_mismatch_strict(monkeypatch):
    monkeypatch.setattr(uso_planner, "generate_structured", _fake_uso_generate_mismatch)
    payload = {"anchors": [_anchor("intro_000", False)], "audio_map": {"style_guidance": "g"}, "visual_brief": _brief()}
    with pytest.raises(RuntimeError):
        build_uso_plan({"render": {"strict_prompt_id_match": True}}, payload)


def test_uso_planner_batches_requests(monkeypatch):
    calls = {"n": 0}

    def _fake(_config, _prompt, _schema):
        calls["n"] += 1
        return {
            "items": [
                {
                    "shot_id": "x",
                    "delta": "gentle gaze shifts left under warm city light",
                    "prompt_text": "A performer turns gently with subtle smile under warm city lights and clean cinematic framing.",
                    "negative_prompt": "low quality, blurry, jpeg artifacts, bad hands",
                }
            ]
        }

    monkeypatch.setattr(uso_planner, "generate_structured", _fake)
    payload = {"anchors": [_anchor("a", False), _anchor("b", False)], "audio_map": {"style_guidance": "g"}, "visual_brief": _brief()}
    out = build_uso_plan(
        {
            "render": {
                "max_shot_sec": 10.0,
                "uso_planner_batch_size": 1,
                "strict_prompt_id_match": False,
            },
        },
        payload,
    )
    assert len(out["items"]) == 2
    assert calls["n"] == 2


def test_uso_planner_strict_batch_mismatch_splits_to_single(monkeypatch):
    monkeypatch.setattr(uso_planner, "generate_structured", _fake_uso_generate_mismatch)
    payload = {"anchors": [_anchor("a", False), _anchor("b", False)], "audio_map": {"style_guidance": "g"}, "visual_brief": _brief()}
    with pytest.raises(RuntimeError, match="shot_id mismatch"):
        build_uso_plan({"render": {"uso_planner_batch_size": 2}}, payload)


def test_uso_anchor_summary_uses_shot_ids_only():
    summary = uso_planner._anchor_summary([_anchor("a", False), _anchor("b", True)])
    assert "a(" in summary
    assert "b(" in summary


def test_uso_normalize_item_id_strips_trailing_punct():
    row = uso_planner._normalize_item_id({"shot_id": "S001_C01."})
    assert row["shot_id"] == "S001_C01"


def test_wan_planner_uses_start_end_only(monkeypatch):
    monkeypatch.setattr(wan_planner, "generate_structured", _fake_wan_generate)
    payload = {"uso_images": [_uso("x", 4.0)], "audio_map": {"lyrics": "[v] line", "style_guidance": "g"}, "visual_brief": _brief()}
    out = build_wan_plan({"video": {"target": "1920x1080@24"}, "render": {"wan_max_clip_sec": 10.0}}, payload)
    assert len(out["clips"]) == 1
    assert out["clips"][0]["shot_id"] == "x"
    assert out["clips"][0]["camera_language"] == "clean hero framing"


def test_wan_planner_shot_id_coerce(monkeypatch):
    monkeypatch.setattr(wan_planner, "generate_structured", _fake_wan_generate_mismatch)
    payload = {"uso_images": [_uso("x", 4.0)], "audio_map": {"lyrics": "[v] line", "style_guidance": "g"}, "visual_brief": _brief()}
    out = build_wan_plan(
        {"video": {"target": "1920x1080@24"}, "render": {"wan_max_clip_sec": 10.0, "strict_prompt_id_match": False}},
        payload,
    )
    assert out["clips"][0]["shot_id"] == "x"
    assert "kitten" in out["clips"][0]["positive_prompt"].lower()


def test_wan_planner_shot_id_mismatch_strict(monkeypatch):
    monkeypatch.setattr(wan_planner, "generate_structured", _fake_wan_generate_mismatch)
    payload = {"uso_images": [_uso("x", 4.0)], "audio_map": {"lyrics": "[v] line", "style_guidance": "g"}, "visual_brief": _brief()}
    with pytest.raises(RuntimeError):
        build_wan_plan(
            {"video": {"target": "1920x1080@24"}, "render": {"wan_max_clip_sec": 10.0, "strict_prompt_id_match": True}},
            payload,
        )


def test_wan_planner_batches_requests(monkeypatch):
    calls = {"n": 0}

    def _fake(_config, _prompt, _schema):
        calls["n"] += 1
        return {"clips": [{"shot_id": "x", "positive_prompt": "p", "negative_prompt": "n", "energy": "normal"}]}

    monkeypatch.setattr(wan_planner, "generate_structured", _fake)
    payload = {"uso_images": [_uso("x", 1.0), _uso("y", 1.0)], "audio_map": {"lyrics": "[v] line", "style_guidance": "g"}, "visual_brief": _brief()}
    out = build_wan_plan(
        {
            "video": {"target": "1920x1080@24"},
            "render": {"wan_planner_batch_size": 1, "strict_prompt_id_match": False},
        },
        payload,
    )
    assert len(out["clips"]) == 2
    assert calls["n"] == 2


def test_wan_planner_strict_batch_mismatch_splits_to_single(monkeypatch):
    monkeypatch.setattr(wan_planner, "generate_structured", _fake_wan_generate_mismatch)
    payload = {"uso_images": [_uso("x", 1.0), _uso("y", 1.0)], "audio_map": {"lyrics": "[v] line", "style_guidance": "g"}, "visual_brief": _brief()}
    with pytest.raises(RuntimeError, match="shot_id mismatch"):
        build_wan_plan({"video": {"target": "1920x1080@24"}, "render": {"wan_planner_batch_size": 2}}, payload)


def test_wan_planner_clip_cap_guard(monkeypatch):
    monkeypatch.setattr(wan_planner, "generate_structured", _fake_wan_generate)
    payload = {"uso_images": [_uso("x", 6.0)], "audio_map": {"lyrics": "[v] line", "style_guidance": "g"}, "visual_brief": _brief()}
    try:
        build_wan_plan({"video": {"target": "1920x1080@24"}, "render": {"wan_max_clip_sec": 5.0}}, payload)
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert "exceeds cap" in str(exc)


def test_wan_planner_clip_cap_guard_default(monkeypatch):
    monkeypatch.setattr(wan_planner, "generate_structured", _fake_wan_generate)
    payload = {"uso_images": [_uso("x", 6.0)], "audio_map": {"lyrics": "[v] line", "style_guidance": "g"}, "visual_brief": _brief()}
    with pytest.raises(RuntimeError):
        build_wan_plan({"video": {"target": "1920x1080@24"}}, payload)


def test_wan_energy_policy_pre_chorus_not_forced_high():
    out = wan_planner._energy_policy({"section_name": "pre_chorus"}, "normal")
    assert out == "normal"


def test_wan_clip_summary_uses_shot_ids_only():
    summary = wan_planner._clip_summary([_uso("x", 1.0), _uso("y", 1.0)])
    assert "x(" in summary
    assert "y(" in summary
    assert "smooth motion" in summary


def test_wan_chains_split_clip_starts_from_previous_end():
    clips = wan_planner._chain_clip_starts(
        [
            {**_uso("S001_C01", 1.0), "start": "s1.png", "end": "e1.png"},
            {**_uso("S001_C02", 1.0), "start": "s2.png", "end": "e2.png"},
            {**_uso("S001_C03", 1.0), "start": "s3.png", "end": "e3.png"},
            {**_uso("S002_C01", 1.0), "start": "s4.png", "end": "e4.png"},
        ]
    )
    assert clips[0]["start"] == "s1.png"
    assert clips[1]["start"] == "e1.png"
    assert clips[2]["start"] == "e2.png"
    assert clips[3]["start"] == "s4.png"


def _anchor(shot_id: str, chorus: bool) -> dict:
    return {
        "shot_id": shot_id,
        "anchor": f"{shot_id}.png",
        "is_chorus": chorus,
        "duration_sec": 4.0,
        "shot_type": "CHAR_MASTER",
        "camera_language": "clean hero framing",
        "pose_delta": "small pose shift",
        "emotion": "steady confidence",
        "scene_detail": "concert light wall",
        "motion_hint": "smooth motion",
    }


def _uso(shot_id: str, duration: float) -> dict:
    return {
        "shot_id": shot_id,
        "start": "s.png",
        "end": "e.png",
        "duration_sec": duration,
        "section_name": "verse",
        "shot_type": "CHAR_MASTER",
        "is_chorus": False,
        "camera_language": "clean hero framing",
        "pose_delta": "small pose shift",
        "emotion": "steady confidence",
        "scene_detail": "concert light wall",
        "motion_hint": "smooth motion",
    }


def _fake_uso_generate(_config, _prompt, _schema):
    return {
        "items": [
            {
                "shot_id": "a",
                "delta": "gentle gaze shifts left with calm breath",
                "prompt_text": "A European girl smiles warmly in a summer flower field.",
                "negative_prompt": "blurry, deformed face, low detail",
            },
            {
                "shot_id": "b",
                "delta": "soft shoulder turn under sunset light",
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


def _fake_wan_generate_mismatch(_config, _prompt, _schema):
    return {
        "clips": [
            {
                "shot_id": "x_alt",
                "positive_prompt": "A kitten made of ice crystals is suddenly awakened and begins to transform into a giant beast with vivid fur.",
                "negative_prompt": "overexposed, static frame, unclear details, low quality",
                "energy": "high",
            }
        ]
    }


def _brief() -> dict:
    return {
        "hero_identity": "silver-haired city-pop heroine",
        "world_rules": "retro neon nightlife with polished stage depth",
        "visual_motifs": ["neon reflections", "chrome microphone"],
        "negative_constraints": ["identity drift", "random fantasy props"],
        "section_briefs": [
            {
                "section_name": "verse",
                "emotional_arc": "steady confidence",
                "palette_hint": "teal-magenta glow",
                "lighting_hint": "soft rim light",
                "staging_hint": "clean stage depth",
            }
        ],
    }
