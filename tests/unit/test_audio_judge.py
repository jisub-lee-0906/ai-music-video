import ai_mv.engines.acestep_1_5_split.audio_judge as audio_judge
import ai_mv.engines.acestep_1_5_split.planner as audio_planner


def test_audio_judge_selects_winner_from_candidates(monkeypatch):
    candidates = [
        {
            "genre_description": "city pop brief",
            "bpm": 108,
            "keyscale": "F# minor",
            "lyrics_blocks": [
                {"label": "Chorus", "lines": ["a", "b", "c", "d", "e", "f"]},
                {"label": "Chorus 2", "lines": ["a2", "b2", "c2", "d2", "e2", "f2"]},
                {"label": "Bridge", "lines": ["bridge one", "bridge two", "bridge three"]},
                {"label": "Final Chorus", "lines": ["fa", "fb", "fc", "fd", "fe", "ff", "fg", "fh"]},
                {"label": "Outro", "lines": ["out one", "out two"]},
            ],
        },
        {
            "genre_description": "better city pop brief",
            "bpm": 110,
            "keyscale": "E minor",
            "lyrics_blocks": [
                {"label": "Chorus", "lines": ["x", "y", "z", "u", "v", "w"]},
                {"label": "Chorus 2", "lines": ["x2", "y2", "z2", "u2", "v2", "w2"]},
                {"label": "Bridge", "lines": ["turn one", "turn two", "turn three"]},
                {"label": "Final Chorus", "lines": ["ga", "gb", "gc", "gd", "ge", "gf", "gg", "gh"]},
                {"label": "Outro", "lines": ["land one", "land two"]},
            ],
        },
    ]

    monkeypatch.setattr(
        audio_judge,
        "generate_structured",
        lambda _config, _prompt, _schema: {
            "winner_index": 1,
            "reasoning": "Candidate 1 has the strongest final payoff.",
            "quality_notes": ["clear hook", "strong bridge", "good outro"],
        },
    )
    out = audio_judge.judge_audio_candidates({}, {"profile_summary": "city-pop"}, candidates)
    assert out["winner_index"] == 1
    assert "strongest final payoff" in out["reasoning"]
    assert out["quality_notes"] == ["clear hook", "strong bridge", "good outro"]


def test_best_passing_candidate_uses_llm_judge(monkeypatch):
    plan = {"profile_summary": "city-pop", "audio_direction": "mature", "hook_direction": "wet glass", "language": "ja"}
    first = {
        "bpm": 108,
        "keyscale": "F# minor",
        "lyrics_blocks": [
            {"label": "Chorus", "lines": ["a", "b", "c", "d", "e", "f"]},
            {"label": "Chorus 2", "lines": ["a2", "b2", "c2", "d2", "e2", "f2"]},
            {"label": "Bridge", "lines": ["bridge one", "bridge two", "bridge three"]},
            {"label": "Final Chorus", "lines": ["fa", "fb", "fc", "fd", "fe", "ff", "fg", "fh"]},
            {"label": "Outro", "lines": ["out one", "out two"]},
        ],
    }
    second = {
        "bpm": 110,
        "keyscale": "E minor",
        "lyrics_blocks": [
            {"label": "Chorus", "lines": ["x", "y", "z", "u", "v", "w"]},
            {"label": "Chorus 2", "lines": ["x2", "y2", "z2", "u2", "v2", "w2"]},
            {"label": "Bridge", "lines": ["turn one", "turn two", "turn three"]},
            {"label": "Final Chorus", "lines": ["ga", "gb", "gc", "gd", "ge", "gf", "gg", "gh"]},
            {"label": "Outro", "lines": ["land one", "land two"]},
        ],
    }
    monkeypatch.setattr(
        audio_planner,
        "judge_audio_candidates",
        lambda _config, _plan, _cands: {
            "winner_index": 0,
            "reasoning": "second is better",
            "quality_notes": ["stronger payoff"],
            "prompt": "judge prompt",
        },
    )
    out = audio_planner._best_passing_candidate({}, plan, [(1, 0, first), (2, 1, second)], [])
    assert out is second
    assert out["audio_quality_review"]["judge"]["winner_index"] == 0
