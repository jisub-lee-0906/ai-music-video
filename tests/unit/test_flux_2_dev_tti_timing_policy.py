import pytest

from ai_mv.engines.flux_2_dev_tti.planner import build_tti_plan
import ai_mv.engines.flux_2_dev_tti.planner as tti_planner


def test_tti_section_timing_policy(monkeypatch):
    monkeypatch.setattr(tti_planner, "generate_structured", _fake_tti_generate_four)
    cfg = {}
    payload = {
        "audio_map": {
            "duration_sec": 80.0,
            "genre_description": "bright city-pop production",
            "lyrics": "[v] line",
            "style_guidance": "g",
            "tags": "city pop, female vocal",
            "sections": [
                {"name": "intro", "start_sec": 0.0, "end_sec": 10.0},
                {"name": "verse", "start_sec": 10.0, "end_sec": 40.0},
                {"name": "chorus", "start_sec": 40.0, "end_sec": 60.0},
                {"name": "outro", "start_sec": 60.0, "end_sec": 80.0},
            ],
        },
        "visual_story_bible": _story_bible(["intro", "verse", "chorus", "outro"]),
        "lyrics_timeline": _timeline(["intro", "verse", "chorus", "outro"], [10.0, 30.0, 20.0, 20.0]),
    }
    out = build_tti_plan(cfg, payload)
    assert out["master_anchor"]["prompt_text"]
    shots = out["shots"]
    assert shots
    assert len(shots) == 4
    verse = [s for s in shots if s["section_name"] == "verse"]
    chorus = [s for s in shots if s["section_name"] == "chorus"]
    assert verse and chorus
    vavg = sum(float(x["duration_sec"]) for x in verse) / len(verse)
    cavg = sum(float(x["duration_sec"]) for x in chorus) / len(chorus)
    assert cavg < vavg
    assert any(bool(s["is_chorus"]) for s in chorus)


def test_tti_distribution_when_sections_exceed_shots(monkeypatch):
    monkeypatch.setattr(tti_planner, "generate_structured", _fake_tti_generate_three)
    cfg = {}
    payload = {
        "audio_map": {
            "duration_sec": 12.0,
            "genre_description": "bright city-pop production",
            "lyrics": "[v] line",
            "style_guidance": "g",
            "tags": "city pop, female vocal",
            "sections": [
                {"name": "intro", "start_sec": 0.0, "end_sec": 2.0},
                {"name": "verse", "start_sec": 2.0, "end_sec": 5.0},
                {"name": "pre_chorus", "start_sec": 5.0, "end_sec": 7.0},
                {"name": "chorus", "start_sec": 7.0, "end_sec": 10.0},
                {"name": "outro", "start_sec": 10.0, "end_sec": 12.0},
            ],
        },
        "visual_story_bible": _story_bible(["intro", "verse", "pre_chorus", "chorus", "outro"]),
        "lyrics_timeline": _timeline(["intro", "verse", "pre_chorus", "chorus", "outro"], [2.0, 3.0, 2.0, 3.0, 2.0]),
    }
    with pytest.raises(RuntimeError, match="shot count mismatch"):
        build_tti_plan(cfg, payload)


def test_tti_duration_scaling_preserves_target_total(monkeypatch):
    monkeypatch.setattr(tti_planner, "generate_structured", _fake_tti_generate_two)
    cfg = {}
    payload = {
        "audio_map": {
            "duration_sec": 10.0,
            "genre_description": "bright city-pop production",
            "lyrics": "[v] line",
            "style_guidance": "g",
            "tags": "city pop, female vocal",
            "sections": [
                {"name": "verse", "start_sec": 0.0, "end_sec": 5.0},
                {"name": "chorus", "start_sec": 5.0, "end_sec": 10.0},
            ],
        },
        "visual_story_bible": _story_bible(["verse", "chorus"]),
        "lyrics_timeline": _timeline(["verse", "chorus"], [5.0, 5.0]),
    }
    out = build_tti_plan(cfg, payload)
    shots = out["shots"]
    assert len(shots) == 2
    assert round(sum(float(x["duration_sec"]) for x in shots), 3) == 10.0
    assert all(float(x["duration_sec"]) > 0 for x in shots)


def test_tti_pre_chorus_not_marked_as_chorus(monkeypatch):
    monkeypatch.setattr(tti_planner, "generate_structured", _fake_tti_generate_two)
    cfg = {}
    payload = {
        "audio_map": {
            "duration_sec": 8.0,
            "genre_description": "bright city-pop production",
            "lyrics": "[v] line",
            "style_guidance": "g",
            "tags": "city pop, female vocal",
            "sections": [
                {"name": "pre_chorus", "start_sec": 0.0, "end_sec": 4.0},
                {"name": "chorus", "start_sec": 4.0, "end_sec": 8.0},
            ],
        },
        "visual_story_bible": _story_bible(["pre_chorus", "chorus"]),
        "lyrics_timeline": _timeline(["pre_chorus", "chorus"], [4.0, 4.0]),
    }
    out = build_tti_plan(cfg, payload)
    shots = out["shots"]
    assert shots[0]["section_name"] == "pre_chorus"
    assert shots[0]["is_chorus"] is False
    assert shots[1]["section_name"] == "chorus"
    assert shots[1]["is_chorus"] is True


def test_tti_plan_allows_missing_creative_seed_fields(monkeypatch):
    monkeypatch.setattr(tti_planner, "generate_structured", _fake_tti_generate_two)
    payload = {
        "audio_map": {
            "duration_sec": 10.0,
            "genre_description": "bright city-pop production",
            "lyrics": "[v] line",
            "style_guidance": "g",
            "tags": "city pop, female vocal",
            "sections": [
                {"name": "verse", "start_sec": 0.0, "end_sec": 5.0},
                {"name": "chorus", "start_sec": 5.0, "end_sec": 10.0},
            ],
        },
        "visual_story_bible": _story_bible(["verse", "chorus"]),
        "lyrics_timeline": _timeline(["verse", "chorus"], [5.0, 5.0]),
    }
    out = build_tti_plan({}, payload)
    assert len(out["shots"]) == 2


def test_tti_preserves_llm_shot_types_for_environment_first_profiles(monkeypatch):
    monkeypatch.setattr(tti_planner, "generate_structured", _fake_tti_generate_five_emotion_close)
    payload = {
        "audio_map": {
            "duration_sec": 20.0,
            "genre_description": "bright city-pop production",
            "lyrics": "[v] line",
            "style_guidance": "g",
            "tags": "city pop, female vocal",
            "sections": [
                {"name": "intro", "start_sec": 0.0, "end_sec": 4.0},
                {"name": "verse", "start_sec": 4.0, "end_sec": 8.0},
                {"name": "pre_chorus", "start_sec": 8.0, "end_sec": 12.0},
                {"name": "chorus", "start_sec": 12.0, "end_sec": 16.0},
                {"name": "outro", "start_sec": 16.0, "end_sec": 20.0},
            ],
        },
        "visual_story_bible": {
            **_story_bible(["intro", "verse", "pre_chorus", "chorus", "outro"]),
            "resolved_profile_policy": {
                "visual_mode": "environment_first",
                "continuity_mode": "same_heroine",
                "face_policy": "avoid",
                "shot_bias": "environment",
                "ref_policy": "minimal",
                "direct_face_sections": [],
                "shot_distribution": {
                    "CHAR_MASTER": 0.08,
                    "EMOTION_CLOSE": 0.04,
                    "PERF_WIDE": 0.22,
                    "ENV_TRANSITION": 0.38,
                    "DETAIL_INSERT": 0.28,
                },
                "face_exposure_defaults": {},
                "ref_triggers": {},
            },
        },
        "lyrics_timeline": _timeline(["intro", "verse", "pre_chorus", "chorus", "outro"], [4.0, 4.0, 4.0, 4.0, 4.0]),
    }
    out = build_tti_plan({}, payload)
    types = [shot["shot_type"] for shot in out["shots"]]
    assert types == ["EMOTION_CLOSE"] * 5


def test_tti_preserves_llm_payoff_closeup_choice(monkeypatch):
    monkeypatch.setattr(tti_planner, "generate_structured", _fake_tti_generate_two_emotion_close)
    story_bible = _story_bible(["verse", "chorus"])
    story_bible["lyric_beats"][1]["payoff_role"] = "release"
    story_bible["section_progression"][1]["story_function"] = "payoff"
    payload = {
        "audio_map": {
            "duration_sec": 10.0,
            "genre_description": "bright city-pop production",
            "lyrics": "[v] line",
            "style_guidance": "g",
            "tags": "city pop, female vocal",
            "sections": [
                {"name": "verse", "start_sec": 0.0, "end_sec": 5.0},
                {"name": "chorus", "start_sec": 5.0, "end_sec": 10.0},
            ],
        },
        "visual_story_bible": {
            **story_bible,
            "resolved_profile_policy": {
                "visual_mode": "balanced",
                "continuity_mode": "same_heroine",
                "face_policy": "payoff_only",
                "shot_bias": "mixed",
                "ref_policy": "identity_sensitive_only",
                "direct_face_sections": ["chorus"],
                "shot_distribution": {
                    "CHAR_MASTER": 0.20,
                    "EMOTION_CLOSE": 0.20,
                    "PERF_WIDE": 0.30,
                    "ENV_TRANSITION": 0.20,
                    "DETAIL_INSERT": 0.10,
                },
                "face_exposure_defaults": {},
                "ref_triggers": {},
            },
        },
        "lyrics_timeline": _timeline(["verse", "chorus"], [5.0, 5.0]),
    }
    out = build_tti_plan({}, payload)
    assert out["shots"][0]["shot_type"] == "EMOTION_CLOSE"
    assert out["shots"][1]["shot_type"] == "EMOTION_CLOSE"
    assert out["shots"][1]["edit_role"] == "release"
    assert out["shots"][1]["mv_function"] == "payoff"
    assert out["shots"][1]["face_exposure_level"] == "direct"


def _story_bible(names: list[str]) -> dict:
    return {
        "hero_identity_lock": "silver-haired nightclub heroine with sharp styling",
        "world_rules": "retro neon nightlife world with polished concert staging",
        "recurring_location_families": ["neon-lit stage runway"],
        "forbidden_drift": ["identity drift", "period change", "random sci-fi props"],
        "lyric_beats": [_beat(name, idx) for idx, name in enumerate(names, start=1)],
        "section_progression": [
            {"section_name": name, "section_label": name, "dominant_emotion": "focused lift", "story_function": "coverage", "lyric_beat_ids": [f"LB{idx:02d}_01"]}
            for idx, name in enumerate(names, start=1)
        ],
        "repeat_escalation_rules": ["repeats must vary"],
    }


def _beat(name: str, idx: int) -> dict:
    return {
        "beat_id": f"LB{idx:02d}_01",
        "section_name": name,
        "section_label": name,
        "line_refs": [1],
        "literal_image": "neon-lit stage runway",
        "visible_action": "walks through the lit stage depth and keeps moving",
        "emotional_turn": "focused lift",
        "continuity_anchor": "pose shift",
        "payoff_role": "develop",
        "repeat_variant_of": "",
        "location_family": "neon-lit stage runway",
        "palette_hint": "teal and magenta",
        "lighting_hint": "soft rim light",
        "camera_commitment": "clean stage depth",
        "space_event": "The stage lights sweep across the runway",
    }


def _timeline(names: list[str], durations: list[float]) -> dict:
    sections = []
    cursor = 0.0
    for idx, (name, duration) in enumerate(zip(names, durations), start=1):
        sections.append(
            {
                "section_name": name,
                "section_label": name,
                "start_sec": cursor,
                "end_sec": cursor + duration,
                "lines": [{"line_index": 1, "text": "line"}],
                "hook_lines": [],
                "lyric_beats": [{"beat_id": f"LB{idx:02d}_01", "line_refs": [1], "start_sec": cursor, "end_sec": cursor + duration}],
            }
        )
        cursor += duration
    return {"sections": sections}


def _fake_tti_generate_four(_config, _prompt, _schema):
    return {"master_anchor": _master(101), "shots": [_shot(i) for i in range(4)]}


def _fake_tti_generate_three(_config, _prompt, _schema):
    return {"master_anchor": _master(201), "shots": [_shot(i, "gentle push-in framing", "small chin lift", "calm intensity", "club light haze", "controlled motion") for i in range(3)]}


def _fake_tti_generate_two(_config, _prompt, _schema):
    return {"master_anchor": _master(301), "shots": [_shot(i) for i in range(2)]}


def _fake_tti_generate_five(_config, _prompt, _schema):
    return {
        "master_anchor": _master(401),
        "shots": [_shot(i, detail=f"detail {i}", shot_type="DETAIL_INSERT") for i in range(5)],
    }


def _fake_tti_generate_five_emotion_close(_config, _prompt, _schema):
    return {
        "master_anchor": _master(402),
        "shots": [_shot(i, detail=f"detail {i}", shot_type="EMOTION_CLOSE") for i in range(5)],
    }


def _fake_tti_generate_two_emotion_close(_config, _prompt, _schema):
    return {
        "master_anchor": _master(403),
        "shots": [_shot(i, shot_type="EMOTION_CLOSE") for i in range(2)],
    }


def _master(seed: int) -> dict:
    return {
        "prompt_text": "hero face, silver hair, bright eyes, stage outfit, satin fabric, poised stance, crystal microphone, neon concert set, rim light, cinematic lens, electric mood, teal pink palette, polished detail",
        "seed": seed,
    }


def _shot(
    idx: int,
    camera: str = "slow dolly with clean mid-wide framing",
    pose: str = "subtle shoulder turn and gaze lift",
    emotion: str = "focused confidence",
    detail: str = "neon stage architecture",
    motion: str = "smooth performance motion",
    shot_type: str = "PERF_WIDE",
) -> dict:
    return {
        "lyric_beat_id": f"LB{idx+1:02d}_01",
        "shot_type": shot_type,
        "camera_language": camera,
        "pose_delta": pose,
        "emotion": emotion,
        "scene_detail": detail,
        "motion_hint": motion,
        "workflow_motion_clause": "moves through the stage depth and holds the camera line",
        "space_relation": "light spill stays camera-right while stage depth opens behind her",
        "edit_role": "release" if idx % 2 else "develop",
        "continuity_lock": "same heroine and world",
        "clip_count": 1,
    }
