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
    assert "lyrics_blocks.lines must be finished sung lyric lines only" in prompt
    assert "AceStep tags text field" in prompt
    assert "Keep fields separated" in prompt
    assert "Do not put planning notes, camera language, or placeholders inside lyrics" in prompt
    assert "Make the chorus immediate" not in prompt
    assert "Let later returns evolve" not in prompt
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
    assert "Keep phrasing natural and singable" in prompt
    assert "Use English sparingly and intentionally" in prompt


def test_audio_prompt_does_not_force_songform_metadata_when_not_requested():
    prompt = audio_planner._audio_prompt(_prompt_plan(duration=0, bar_lane="intro 4, verse 12"))
    assert "Target duration=" not in prompt
    assert "Bar lane=" not in prompt
    assert "Hook contour bias=" not in prompt


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


def test_normalize_and_validate_keeps_llm_duration_when_not_overridden(monkeypatch):
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
    assert normalized["duration"] == 999


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
