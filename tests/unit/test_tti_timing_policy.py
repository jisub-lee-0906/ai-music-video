import pytest

from ai_mv.engines.flux_1_dev_tti.planner import build_tti_plan
import ai_mv.engines.flux_1_dev_tti.planner as tti_planner


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
        "visual_brief": _brief(["intro", "verse", "chorus", "outro"]),
    }
    out = build_tti_plan(cfg, payload)
    assert out["master_anchor"]["prompt_clip_l"]
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
        "visual_brief": _brief(["intro", "verse", "pre_chorus", "chorus", "outro"]),
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
        "visual_brief": _brief(["verse", "chorus"]),
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
        "visual_brief": _brief(["pre_chorus", "chorus"]),
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
        "visual_brief": _brief(["verse", "chorus"]),
    }
    out = build_tti_plan({}, payload)
    assert len(out["shots"]) == 2


def _brief(names: list[str]) -> dict:
    return {
        "hero_identity": "silver-haired nightclub heroine with sharp styling",
        "world_rules": "retro neon nightlife world with polished concert staging",
        "visual_motifs": ["neon reflections", "chrome microphone", "teal-magenta glow"],
        "negative_constraints": ["identity drift", "period change", "random sci-fi props"],
        "section_briefs": [_section(name) for name in names],
    }


def _section(name: str) -> dict:
    return {
        "section_name": name,
        "emotional_arc": "focused lift",
        "palette_hint": "teal and magenta",
        "lighting_hint": "soft rim light",
        "staging_hint": "clean stage depth",
    }


def _fake_tti_generate_four(_config, _prompt, _schema):
    return {"master_anchor": _master(101), "shots": [_shot(i) for i in range(4)]}


def _fake_tti_generate_three(_config, _prompt, _schema):
    return {"master_anchor": _master(201), "shots": [_shot(i, "gentle push-in framing", "small chin lift", "calm intensity", "club light haze", "controlled motion") for i in range(3)]}


def _fake_tti_generate_two(_config, _prompt, _schema):
    return {"master_anchor": _master(301), "shots": [_shot(i) for i in range(2)]}


def _master(seed: int) -> dict:
    return {
        "prompt_clip_l": "hero face, silver hair, bright eyes, stage outfit, satin fabric, poised stance, crystal mic, neon set, rim light, cinematic lens, electric mood, teal pink palette, polished detail",
        "prompt_t5xxl": "A silver-haired performer stands in a neon concert set with a crystal microphone and a sharply styled satin stage outfit. Clean lens framing and rim lighting hold a poised, magnetic stage presence.",
        "negative_prompt": "low quality, blurry, bad hands",
        "seed": seed,
    }


def _shot(
    idx: int,
    camera: str = "slow dolly with clean mid-wide framing",
    pose: str = "subtle shoulder turn and gaze lift",
    emotion: str = "focused confidence",
    detail: str = "neon stage architecture",
    motion: str = "smooth performance motion",
) -> dict:
    return {
        "shot_id": f"s_{idx:03d}",
        "shot_type": "PERF_WIDE",
        "is_chorus": False,
        "camera_language": camera,
        "pose_delta": pose,
        "emotion": emotion,
        "scene_detail": detail,
        "motion_hint": motion,
    }
