import ai_mv.engines.acestep_1_5_aio.planner as audio_planner


def _prompt_plan(**extra):
    plan = {
        "tags": "city pop, neon",
        "language": "ja",
        "profile_intent": {
            "audio_intent": {
                "brief": "mature female vocal, glossy piano, disco bounce",
                "hook_brief": "neon rain and chrome reflections",
            },
            "world_intent": {
                "visual_intent": "warm urban nightlife",
                "story_world": "retro city-pop lane",
                "action_vocabulary": "small graceful actions",
                "payoff_style": "clear return",
            },
            "negative_intent": {
                "visual_negative": "no futuristic sci-fi tone",
                "mv_avoid": "",
            },
        },
        "duration": 200,
        "bpm": 108,
        "seed": 31,
        "quality": "high",
        "filename_prefix": "run_audio",
    }
    plan.update(extra)
    return plan


def test_audio_prompt_focuses_on_prompt_engineering_not_checklist():
    prompt = audio_planner._audio_prompt(_prompt_plan())
    assert "Return JSON only" in prompt
    assert "Allowed section values only" in prompt
    assert "lyrics_blocks.lines must contain only finished sung lyric lines" in prompt
    assert "Write like a finished record" in prompt
    assert "Front-load memorability" in prompt
    assert "emotionally inevitable" in prompt
    assert "Make the chorus easy to sing back after one listen" in prompt
    assert "Keep the fields strictly separated" in prompt
    assert "Do not leak world-building labels or visual planning vocabulary directly into lyric lines" in prompt
    assert "Style guidance=" not in prompt
    assert "Visual carryover=" not in prompt
    assert "Audio intent=mature female vocal, glossy piano, disco bounce." in prompt
    assert "World intent=warm urban nightlife." in prompt
    assert "Hook intent=neon rain and chrome reflections." in prompt
    assert "Story world=retro city-pop lane." in prompt
    assert "Avoid=no futuristic sci-fi tone." in prompt
    assert "quality failure" not in prompt
    assert "heuristic" not in prompt


def test_audio_prompt_keeps_language_direction_in_prompt_only():
    prompt = audio_planner._audio_prompt(_prompt_plan())
    assert "Lyrics language=ja." in prompt
    assert "Write fluent modern Japanese lyrics" in prompt
    assert "Avoid forced transliterations" in prompt
    assert "Keep English rare and intentional" in prompt


def test_audio_prompt_includes_hook_shape_bias():
    prompt = audio_planner._audio_prompt(_prompt_plan(hook_shape_bias="reflection cue with afterglow or remaining heat"))
    assert "Hook contour bias=" in prompt


def test_audio_prompt_includes_bar_lane():
    prompt = audio_planner._audio_prompt(_prompt_plan(bar_lane="intro 4, verse 12, pre 8, chorus 12, final chorus 16, outro 4"))
    assert "Bar lane=intro 4, verse 12, pre 8, chorus 12, final chorus 16, outro 4." in prompt


def test_normalize_and_validate_keeps_prompt_first_behavior(monkeypatch):
    monkeypatch.setattr(
        audio_planner,
        "_plan_with_llm",
        lambda _config, _plan: {
            "genre_description": "日本語でも 통과",
            "bpm": 108,
            "keyscale": "",
            "seed": 31,
            "duration": 200,
            "lyrics_blocks": [
                {"section": "chorus", "label": "Chorus", "style": "lift", "lines": ["Stay with me all night"]},
                {"section": "chorus", "label": "Final Chorus", "style": "peak", "lines": ["Stay with me all night again"]},
            ],
        },
    )
    normalized = audio_planner._normalize_and_validate({}, _prompt_plan(language="ja", keyscale="F# minor"))
    assert normalized["genre_description"] == "日本語でも 통과"
    assert normalized["language"] == "ja"
    assert normalized["keyscale"] == "F# minor"


def test_normalize_and_validate_recomputes_duration_from_generated_songform(monkeypatch):
    monkeypatch.setattr(
        audio_planner,
        "_plan_with_llm",
        lambda _config, _plan: {
            "genre_description": "brief",
            "bpm": 120,
            "keyscale": "",
            "seed": 31,
            "duration": 999,
            "lyrics_blocks": [
                {"section": "intro", "label": "Intro", "style": "set", "lines": ["a"]},
                {"section": "verse_1", "label": "Verse 1", "style": "move", "lines": ["b"]},
                {"section": "chorus", "label": "Final Chorus", "style": "peak", "lines": ["c"]},
                {"section": "outro", "label": "Outro", "style": "land", "lines": ["d"]},
            ],
        },
    )
    normalized = audio_planner._normalize_and_validate({}, _prompt_plan(duration=200))
    assert normalized["duration"] == 72


def test_plan_once_returns_single_pass_plan_without_quality_review(monkeypatch):
    monkeypatch.setattr(
        audio_planner,
        "_normalize_and_validate",
        lambda _config, plan: {
            "genre_description": "brief",
            "bpm": 108,
            "keyscale": "F# minor",
            "seed": plan["seed"],
            "duration": 200,
            "lyrics": "[Chorus]\nfirst hook",
            "lyrics_blocks": [
                {"section": "chorus", "label": "Chorus", "style": "lift", "lines": ["first hook"]},
            ],
        },
    )
    result = audio_planner._plan_once({}, _prompt_plan())
    assert result["seed"] == 31
    assert "audio_quality_review" not in result
