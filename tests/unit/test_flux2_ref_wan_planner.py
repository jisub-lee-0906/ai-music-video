import pytest

from ai_mv.core.contracts.prompt_normalize import normalize_flux2_ref_items, normalize_wan_clips
from ai_mv.engines.flux2_reference.planner import build_flux2_ref_plan
from ai_mv.engines.wan_2_2_flf2v.planner import build_wan_plan
import ai_mv.engines.flux2_reference.planner as flux2_ref_planner
import ai_mv.engines.wan_2_2_flf2v.planner as wan_planner


def test_flux2_ref_planner_double(monkeypatch):
    monkeypatch.setattr(flux2_ref_planner, "generate_structured", _fake_flux2_ref_generate)
    payload = {"clip_routes": [_route("a", True), _route("b", True)], "audio_map": {"style_guidance": "g"}, "visual_brief": _brief()}
    out = build_flux2_ref_plan({}, payload)
    shot_ids = [x["shot_id"] for x in out["items"]]
    assert shot_ids == ["a", "b"]
    assert out["items"][0]["prompt_text"]
    assert out["items"][0]["subject_clause"]
    assert "left-to-right" in out["items"][0]["prompt_text"]


def test_flux2_ref_planner_allows_missing_style_guidance(monkeypatch):
    monkeypatch.setattr(flux2_ref_planner, "generate_structured", _fake_flux2_ref_generate_single_a)
    payload = {"clip_routes": [_route("a", True)], "visual_brief": _brief()}
    out = build_flux2_ref_plan({}, payload)
    assert out["items"][0]["prompt_text"]
    assert out["items"][0]["action_clause"]
    assert "style_guidance" not in out["items"][0]


def test_flux2_ref_planner_shot_id_coerce(monkeypatch):
    monkeypatch.setattr(flux2_ref_planner, "generate_structured", _fake_flux2_ref_generate_mismatch)
    payload = {"clip_routes": [_route("a", True)], "audio_map": {"style_guidance": "g"}, "visual_brief": _brief()}
    with pytest.raises(RuntimeError, match="shot_id mismatch"):
        build_flux2_ref_plan({}, payload)


def test_flux2_ref_planner_shot_id_mismatch_strict(monkeypatch):
    monkeypatch.setattr(flux2_ref_planner, "generate_structured", _fake_flux2_ref_generate_mismatch)
    payload = {"clip_routes": [_route("a", True)], "audio_map": {"style_guidance": "g"}, "visual_brief": _brief()}
    with pytest.raises(RuntimeError):
        build_flux2_ref_plan({}, payload)


def test_flux2_ref_planner_batches_requests(monkeypatch):
    calls = {"n": 0}

    def _fake(_config, _prompt, _schema):
        calls["n"] += 1
        shot_id = "a" if calls["n"] == 1 else "b"
        return {
            "items": [
                {
                    "shot_id": shot_id,
                    "subject_clause": "A performer in a clean medium frame",
                    "action_clause": "turns gently toward the light",
                    "environment_clause": "under warm city reflections",
                    "continuity_clause": "keeping the same left-to-right drift",
                }
            ]
        }

    monkeypatch.setattr(flux2_ref_planner, "generate_structured", _fake)
    payload = {"clip_routes": [_route("a", True), _route("b", True)], "audio_map": {"style_guidance": "g"}, "visual_brief": _brief()}
    out = build_flux2_ref_plan(
        {
            "render": {
                "flux2_ref_planner_batch_size": 1,
            },
        },
        payload,
    )
    assert len(out["items"]) == 2
    assert calls["n"] == 2


def test_flux2_ref_planner_strict_batch_mismatch_splits_to_single(monkeypatch):
    monkeypatch.setattr(flux2_ref_planner, "generate_structured", _fake_flux2_ref_generate_mismatch)
    payload = {"clip_routes": [_route("a", True), _route("b", True)], "audio_map": {"style_guidance": "g"}, "visual_brief": _brief()}
    with pytest.raises(RuntimeError, match="shot_id mismatch"):
        build_flux2_ref_plan({"render": {"flux2_ref_planner_batch_size": 2}}, payload)


def test_flux2_ref_plan_empty_when_no_ref_routes():
    out = build_flux2_ref_plan({}, {"clip_routes": [], "audio_map": {}, "visual_brief": _brief()})
    assert out["items"] == []


def test_flux2_ref_normalize_missing_shot_id_raises_runtimeerror():
    with pytest.raises(RuntimeError, match="Flux2 reference planner missing shot_id: missing"):
        normalize_flux2_ref_items(
            [
                {
                    "shot_id": "other",
                    "subject_clause": "A performer in frame",
                    "action_clause": "turns toward the light",
                    "environment_clause": "under wet neon",
                    "continuity_clause": "keeping the same lane relation",
                }
            ],
            [{"shot_id": "missing"}],
        )


def test_flux2_ref_normalize_duplicate_shot_id_fails():
    with pytest.raises(RuntimeError, match="duplicate shot_id: a"):
        normalize_flux2_ref_items(
            [
                {
                    "shot_id": "a",
                    "subject_clause": "A performer in frame",
                    "action_clause": "turns toward the light",
                    "environment_clause": "under wet neon",
                    "continuity_clause": "keeping the same lane relation",
                },
                {
                    "shot_id": "a",
                    "subject_clause": "A performer in frame",
                    "action_clause": "steps toward the light",
                    "environment_clause": "under wet neon",
                    "continuity_clause": "keeping the same lane relation",
                },
            ],
            [{"shot_id": "a"}],
        )


def test_flux2_ref_normalize_unknown_extra_shot_id_fails():
    with pytest.raises(RuntimeError, match="unknown shot_id: extra"):
        normalize_flux2_ref_items(
            [
                {
                    "shot_id": "a",
                    "subject_clause": "A performer in frame",
                    "action_clause": "turns toward the light",
                    "environment_clause": "under wet neon",
                    "continuity_clause": "keeping the same lane relation",
                },
                {
                    "shot_id": "extra",
                    "subject_clause": "A performer in frame",
                    "action_clause": "steps toward the light",
                    "environment_clause": "under wet neon",
                    "continuity_clause": "keeping the same lane relation",
                },
            ],
            [{"shot_id": "a"}],
        )


def test_flux2_ref_anchor_summary_uses_shot_ids_only():
    summary = flux2_ref_planner._anchor_summary([_route("a", False), _route("b", True)])
    assert "a(" in summary
    assert "b(" in summary


def test_flux2_ref_normalize_item_id_strips_trailing_punct():
    row = flux2_ref_planner._normalize_item_id({"shot_id": "S001_C01."})
    assert row["shot_id"] == "S001_C01"


def test_wan_planner_uses_start_end_only(monkeypatch):
    monkeypatch.setattr(wan_planner, "generate_structured", _fake_wan_generate)
    payload = {
        "clip_routes": [_route("x", False)],
        "flux2_ref_images": [_flux2_ref("x", 4.0)],
        "audio_map": {"style_guidance": "g"},
        "visual_brief": _brief(),
    }
    out = build_wan_plan({"video": {"target": "1920x1080@24"}, "render": {"wan_max_clip_sec": 10.0}}, payload)
    assert len(out["clips"]) == 1
    assert out["clips"][0]["shot_id"] == "x"
    assert out["clips"][0]["camera_language"] == "clean hero framing"
    assert out["clips"][0]["positive_prompt"]
    assert out["clips"][0]["subject_motion"]
    assert out["clips"][0]["camera_relation"]
    assert "Glides back without breaking alignment" in out["clips"][0]["positive_prompt"]


def test_wan_planner_shot_id_coerce(monkeypatch):
    monkeypatch.setattr(wan_planner, "generate_structured", _fake_wan_generate_mismatch)
    payload = {"clip_routes": [_route("x", False)], "flux2_ref_images": [_flux2_ref("x", 4.0)], "audio_map": {"style_guidance": "g"}, "visual_brief": _brief()}
    with pytest.raises(RuntimeError, match="shot_id mismatch"):
        build_wan_plan({"video": {"target": "1920x1080@24"}, "render": {"wan_max_clip_sec": 10.0}}, payload)


def test_wan_planner_shot_id_mismatch_strict(monkeypatch):
    monkeypatch.setattr(wan_planner, "generate_structured", _fake_wan_generate_mismatch)
    payload = {"clip_routes": [_route("x", False)], "flux2_ref_images": [_flux2_ref("x", 4.0)], "audio_map": {"style_guidance": "g"}, "visual_brief": _brief()}
    with pytest.raises(RuntimeError):
        build_wan_plan({"video": {"target": "1920x1080@24"}, "render": {"wan_max_clip_sec": 10.0}}, payload)


def test_wan_planner_batches_requests(monkeypatch):
    calls = {"n": 0}

    def _fake(_config, _prompt, _schema):
        calls["n"] += 1
        shot_id = "x" if calls["n"] == 1 else "y"
        return {
            "clips": [
                {
                    "shot_id": shot_id,
                    "subject_motion": "She holds at the curb and steps into the crossing with a measured stride",
                    "camera_relation": "glides back in a steady front relation",
                    "environment_detail": "Wet stripes brighten under her stride",
                    "negative_prompt": "overexposed, static frame, low quality",
                    "energy": "normal",
                }
            ]
        }

    monkeypatch.setattr(wan_planner, "generate_structured", _fake)
    payload = {"clip_routes": [_route("x", False), _route("y", False)], "flux2_ref_images": [_flux2_ref("x", 1.0), _flux2_ref("y", 1.0)], "audio_map": {"style_guidance": "g"}, "visual_brief": _brief()}
    out = build_wan_plan(
        {
            "video": {"target": "1920x1080@24"},
            "render": {"wan_planner_batch_size": 1},
        },
        payload,
    )
    assert len(out["clips"]) == 2
    assert calls["n"] == 2


def test_wan_planner_strict_batch_mismatch_splits_to_single(monkeypatch):
    monkeypatch.setattr(wan_planner, "generate_structured", _fake_wan_generate_mismatch)
    payload = {"clip_routes": [_route("x", False), _route("y", False)], "flux2_ref_images": [_flux2_ref("x", 1.0), _flux2_ref("y", 1.0)], "audio_map": {"style_guidance": "g"}, "visual_brief": _brief()}
    with pytest.raises(RuntimeError, match="shot_id mismatch"):
        build_wan_plan({"video": {"target": "1920x1080@24"}, "render": {"wan_planner_batch_size": 2}}, payload)


def test_wan_normalize_missing_shot_id_raises_runtimeerror():
    with pytest.raises(RuntimeError, match="WAN planner missing shot_id: missing"):
        normalize_wan_clips(
            [
                {
                    "shot_id": "other",
                    "subject_motion": "She crosses the lane and lifts her eyes",
                    "camera_relation": "holds a close side profile",
                    "environment_detail": "wet stripes brighten below",
                    "negative_prompt": "overexposed, static frame, low quality",
                    "energy": "normal",
                }
            ],
            [{"shot_id": "missing"}],
        )


def test_wan_normalize_duplicate_shot_id_fails():
    with pytest.raises(RuntimeError, match="duplicate shot_id: x"):
        normalize_wan_clips(
            [
                {
                    "shot_id": "x",
                    "subject_motion": "She crosses the lane and lifts her eyes",
                    "camera_relation": "holds a close side profile",
                    "environment_detail": "wet stripes brighten below",
                    "negative_prompt": "overexposed, static frame, low quality",
                    "energy": "normal",
                },
                {
                    "shot_id": "x",
                    "subject_motion": "She settles near the curb and looks ahead",
                    "camera_relation": "holds a close side profile",
                    "environment_detail": "wet stripes brighten below",
                    "negative_prompt": "overexposed, static frame, low quality",
                    "energy": "normal",
                },
            ],
            [{"shot_id": "x"}],
        )


def test_wan_normalize_unknown_extra_shot_id_fails():
    with pytest.raises(RuntimeError, match="unknown shot_id: extra"):
        normalize_wan_clips(
            [
                {
                    "shot_id": "x",
                    "subject_motion": "She crosses the lane and lifts her eyes",
                    "camera_relation": "holds a close side profile",
                    "environment_detail": "wet stripes brighten below",
                    "negative_prompt": "overexposed, static frame, low quality",
                    "energy": "normal",
                },
                {
                    "shot_id": "extra",
                    "subject_motion": "She settles near the curb and looks ahead",
                    "camera_relation": "holds a close side profile",
                    "environment_detail": "wet stripes brighten below",
                    "negative_prompt": "overexposed, static frame, low quality",
                    "energy": "normal",
                },
            ],
            [{"shot_id": "x"}],
        )


def test_wan_planner_clip_cap_guard(monkeypatch):
    monkeypatch.setattr(wan_planner, "generate_structured", _fake_wan_generate)
    payload = {"clip_routes": [_route("x", False, duration=6.0)], "flux2_ref_images": [_flux2_ref("x", 6.0)], "audio_map": {"style_guidance": "g"}, "visual_brief": _brief()}
    try:
        build_wan_plan({"video": {"target": "1920x1080@24"}, "render": {"wan_max_clip_sec": 5.0}}, payload)
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert "exceeds cap" in str(exc)


def test_wan_planner_clip_cap_guard_default(monkeypatch):
    monkeypatch.setattr(wan_planner, "generate_structured", _fake_wan_generate)
    payload = {"clip_routes": [_route("x", False, duration=6.0)], "flux2_ref_images": [_flux2_ref("x", 6.0)], "audio_map": {"style_guidance": "g"}, "visual_brief": _brief()}
    with pytest.raises(RuntimeError):
        build_wan_plan({"video": {"target": "1920x1080@24"}}, payload)


def test_wan_energy_policy_pre_chorus_not_forced_high():
    out = wan_planner._energy_policy({"section_name": "pre_chorus"}, "normal")
    assert out == "normal"


def test_wan_clip_summary_uses_shot_ids_only():
    summary = wan_planner._clip_summary([_route("x", False), _route("y", False)])
    assert "x(" in summary
    assert "y(" in summary
    assert "smooth motion" in summary


def test_wan_chains_split_clip_starts_from_previous_end():
    clips = wan_planner._chain_clip_starts(
        [
            {**_flux2_ref("S001_C01", 1.0), "start": "s1.png", "end": "e1.png"},
            {**_flux2_ref("S001_C02", 1.0), "start": "s2.png", "end": "e2.png"},
            {**_flux2_ref("S001_C03", 1.0), "start": "s3.png", "end": "e3.png"},
            {**_flux2_ref("S002_C01", 1.0), "start": "s4.png", "end": "e4.png"},
        ]
    )
    assert clips[0]["start"] == "s1.png"
    assert clips[1]["start"] == "e1.png"
    assert clips[2]["start"] == "e2.png"
    assert clips[3]["start"] == "s4.png"


def test_wan_normalize_allows_concrete_quality_words_when_motion_is_readable():
    out = normalize_wan_clips(
        [
            {
                "shot_id": "x",
                "subject_motion": "She keeps a clear forward walk line and settles into a shorter final step",
                "camera_relation": "holds a close side profile",
                "environment_detail": "clean neon reflections stretch along the crossing",
                "negative_prompt": "overexposed, static frame, low quality",
                "energy": "normal",
            }
        ],
        [{"shot_id": "x"}],
    )
    assert out["x"]["subject_motion"].startswith("She keeps a clear forward walk line")


def _anchor(shot_id: str, chorus: bool) -> dict:
    return _route(shot_id, chorus)


def _flux2_ref(shot_id: str, duration: float) -> dict:
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


def _route(shot_id: str, chorus: bool, duration: float = 4.0) -> dict:
    return {
        "shot_id": shot_id,
        "anchor": f"{shot_id}.png",
        "identity_anchor": f"{shot_id}.png",
        "is_chorus": chorus,
        "duration_sec": duration,
        "section_name": "chorus" if chorus else "verse",
        "section_label": "Final Chorus" if chorus else "Verse 1",
        "shot_type": "EMOTION_CLOSE" if chorus else "CHAR_MASTER",
        "camera_language": "clean hero framing",
        "pose_delta": "small pose shift",
        "emotion": "steady confidence",
        "scene_detail": "concert light wall",
        "motion_hint": "smooth motion",
        "space_relation": "glass stays camera-right",
        "clip_index": 1,
        "clip_count": 1,
        "hero_frame_score": 4 if chorus else 2,
        "consistency_need": "high" if chorus else "low",
        "mv_function": "payoff" if chorus else "coverage",
        "return_weight": 4 if chorus else 1,
        "use_ref": chorus,
        "route_reason": "priority return section" if chorus else "tti-only coverage shot",
    }


def _fake_flux2_ref_generate(_config, _prompt, _schema):
    return {
        "items": [
            {
                "shot_id": "a",
                "subject_clause": "A European girl with a heartfelt smile",
                "action_clause": "lets her gaze drift left",
                "environment_clause": "in a summer flower field",
                "continuity_clause": "keeping the same left-to-right field relation",
            },
            {
                "shot_id": "b",
                "subject_clause": "A performer with calm expression",
                "action_clause": "turns one shoulder under sunset light",
                "environment_clause": "against a soft evening horizon",
                "continuity_clause": "holding the same side-profile direction",
            },
        ]
    }


def _fake_flux2_ref_generate_single_a(_config, _prompt, _schema):
    return {
        "items": [
            {
                "shot_id": "a",
                "subject_clause": "A European girl with a heartfelt smile",
                "action_clause": "lets her gaze drift left",
                "environment_clause": "in a summer flower field",
                "continuity_clause": "keeping the same open field relation",
            }
        ]
    }


def _fake_flux2_ref_generate_mismatch(_config, _prompt, _schema):
    return {
        "items": [
            {
                "shot_id": "intro_001",
                "subject_clause": "A European girl with a heartfelt smile",
                "action_clause": "holds a small gaze shift",
                "environment_clause": "in an endless blooming flower field",
                "continuity_clause": "keeping the same summer sky behind her",
            }
        ]
    }


def _fake_wan_generate(_config, _prompt, _schema):
    return {
        "clips": [
            {
                "shot_id": "x",
                "subject_motion": "She faces forward at the curb and steps into the lane with steady rhythm",
                "camera_relation": "glides back without breaking alignment",
                "environment_detail": "Wet light gathers underfoot",
                "negative_prompt": "overexposed, static frame, unclear details, low quality",
                "energy": "normal",
            },
        ]
    }


def _fake_wan_generate_mismatch(_config, _prompt, _schema):
    return {
        "clips": [
            {
                "shot_id": "x_alt",
                "subject_motion": "A kitten made of ice crystals jolts awake and drifts into a giant beast transformation",
                "camera_relation": "holds a close frame while the body expands",
                "environment_detail": "Colored fur catches the harsh light",
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
