from ai_mv.engines.flux_1_dev_tti.planner import build_tti_plan
import ai_mv.engines.flux_1_dev_tti.planner as tti_planner


def test_tti_section_timing_policy(monkeypatch):
    monkeypatch.setattr(tti_planner, "generate_structured", _fake_tti_generate)
    cfg = {
        "style": {"guidance": "g"},
        "audio": {"song_title": "t", "song_description": "d", "lyrics": "[v] line"},
    }
    payload = {
        "audio_map": {
            "duration_sec": 80.0,
            "sections": [
                {"name": "intro", "start_sec": 0.0, "end_sec": 10.0},
                {"name": "verse", "start_sec": 10.0, "end_sec": 40.0},
                {"name": "chorus", "start_sec": 40.0, "end_sec": 60.0},
                {"name": "outro", "start_sec": 60.0, "end_sec": 80.0},
            ],
        }
    }
    out = build_tti_plan(cfg, payload)
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
    monkeypatch.setattr(tti_planner, "generate_structured", _fake_tti_generate_small)
    cfg = {
        "style": {"guidance": "g"},
        "audio": {"song_title": "t", "song_description": "d", "lyrics": "[v] line"},
    }
    payload = {
        "audio_map": {
            "duration_sec": 12.0,
            "sections": [
                {"name": "intro", "start_sec": 0.0, "end_sec": 2.0},
                {"name": "verse", "start_sec": 2.0, "end_sec": 5.0},
                {"name": "pre_chorus", "start_sec": 5.0, "end_sec": 7.0},
                {"name": "chorus", "start_sec": 7.0, "end_sec": 10.0},
                {"name": "outro", "start_sec": 10.0, "end_sec": 12.0},
            ],
        }
    }
    out = build_tti_plan(cfg, payload)
    shots = out["shots"]
    assert len(shots) == 5
    assert round(sum(float(x["duration_sec"]) for x in shots), 3) == 12.0


def test_tti_duration_scaling_preserves_target_total(monkeypatch):
    monkeypatch.setattr(tti_planner, "generate_structured", _fake_tti_generate_many)
    cfg = {
        "style": {"guidance": "g"},
        "audio": {"song_title": "t", "song_description": "d", "lyrics": "[v] line"},
    }
    payload = {
        "audio_map": {
            "duration_sec": 10.0,
            "sections": [
                {"name": "verse", "start_sec": 0.0, "end_sec": 5.0},
                {"name": "chorus", "start_sec": 5.0, "end_sec": 10.0},
            ],
        }
    }
    out = build_tti_plan(cfg, payload)
    shots = out["shots"]
    assert len(shots) == 2
    assert round(sum(float(x["duration_sec"]) for x in shots), 3) == 10.0
    assert all(float(x["duration_sec"]) > 0 for x in shots)


def _fake_tti_generate(_config, _prompt, _schema):
    base = {
        "prompt_clip_l": "a, b, c, d, e, f, g, h, i, j, k, l, m",
        "prompt_t5xxl": "Sentence one. Sentence two.",
        "negative_prompt": "n",
        "duration_sec": 6.0,
        "seed": 1,
        "shot_type": "PERF_WIDE",
        "is_chorus": False,
    }
    shots = []
    for i in range(8):
        row = dict(base)
        row["shot_id"] = f"s_{i:03d}"
        row["seed"] = 100 + i
        shots.append(row)
    return {"shots": shots}


def _fake_tti_generate_small(_config, _prompt, _schema):
    base = {
        "prompt_clip_l": "a, b, c, d, e, f, g, h, i, j, k, l, m",
        "prompt_t5xxl": "Sentence one. Sentence two.",
        "negative_prompt": "n",
        "duration_sec": 4.0,
        "seed": 1,
        "shot_type": "PERF_WIDE",
        "is_chorus": False,
    }
    shots = []
    for i in range(3):
        row = dict(base)
        row["shot_id"] = f"s_{i:03d}"
        row["seed"] = 200 + i
        shots.append(row)
    return {"shots": shots}


def _fake_tti_generate_many(_config, _prompt, _schema):
    return _fake_tti_generate(_config, _prompt, _schema)
