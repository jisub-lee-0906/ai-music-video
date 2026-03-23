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


def test_audio_prompt_focuses_on_outline_planning_not_lyrics_dump():
    prompt = audio_planner._audio_prompt(_prompt_plan())
    assert "Return JSON only" in prompt
    assert "Allowed section values only" in prompt
    assert "For this planning step, do not write lyric lines yet" in prompt
    assert "label is the internal section header and must use the canonical English song labels only" in prompt
    assert "Do not make Verse 2 feel like a copy-paste replay of Verse 1" in prompt
    assert "Only use post_chorus when the hook benefits from one extra tag" in prompt
    assert "Make the final chorus unmistakably bigger or more complete than earlier choruses" in prompt


def test_audio_outline_prompt_keeps_language_direction():
    prompt = audio_planner._audio_prompt(_prompt_plan())
    assert "Lyrics language=ja." in prompt
    assert "Write fluent modern Japanese lyrics" in prompt
    assert "avoid untranslated English nouns" in prompt
    assert "canonical English section labels exactly as provided in the outline" in prompt


def test_audio_lyrics_prompt_locks_outline_and_requests_lines_only():
    prompt = audio_planner._audio_lyrics_prompt(
        _prompt_plan(),
        {
            "genre_description": "Japanese city pop: glossy electric piano",
            "bpm": 108,
            "keyscale": "A major",
            "seed": 31,
            "duration": 200,
            "lyrics_blocks": [
                {"section": "verse_1", "label": "Verse 1", "style": "lift", "line_count": 4},
                {"section": "chorus", "label": "Final Chorus", "style": "peak", "line_count": 5},
            ],
        },
    )
    assert "Locked outline:" in prompt
    assert "[Verse 1] section=verse_1 style=lift line_count=4" in prompt
    assert "Allowed headers only: [Verse 1] | [Final Chorus]." in prompt
    assert "Write plain text only. Do not output JSON." in prompt
    assert "Do not leave any Latin alphabet words" in prompt
    assert "Final Chorus must keep at most two reused lines" in prompt


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
            "genre_description": "Japanese city pop: glossy electric piano",
            "bpm": 108,
            "keyscale": "",
            "seed": 31,
            "duration": 200,
            "lyrics_blocks": [
                {"section": "chorus", "label": "Chorus", "style": "lift", "lines": ["濡れた縁石にネオンが割れる", "改札の音が静かに消える", "窓の帯が頬をかすめる", "まだ夜は終わらない"]},
                {"section": "chorus", "label": "Final Chorus", "style": "peak", "lines": ["濡れた縁石にネオンが割れる", "改札の音が静かに消える", "帰り道まで光が伸びる", "この街ごと抱きしめていく"]},
            ],
        },
    )
    normalized = audio_planner._normalize_and_validate({}, _prompt_plan(language="ja", keyscale="F# minor"))
    assert normalized["genre_description"] == "Japanese city pop: glossy electric piano"
    assert normalized["language"] == "ja"
    assert normalized["keyscale"] == "F# minor"


def test_plan_lyrics_with_llm_uses_ollama_text_generation(monkeypatch):
    monkeypatch.setattr(
        audio_planner,
        "generate_ollama_text",
        lambda _config, _prompt, **_kwargs: "a\nb\nc\nd",
    )
    merged = audio_planner._plan_lyrics_with_llm(
        {},
        _prompt_plan(),
        {
            "genre_description": "Japanese city pop: glossy electric piano",
            "bpm": 108,
            "keyscale": "A major",
            "seed": 31,
            "duration": 200,
            "lyrics_blocks": [
                {"section": "verse_1", "label": "Verse 1", "style": "lift", "line_count": 4},
            ],
        },
    )
    assert merged["lyrics_blocks"][0]["lines"] == ["a", "b", "c", "d"]


def test_parse_audio_lyrics_block_lines_requires_exact_count():
    lines = audio_planner._parse_audio_lyrics_block_lines(
        {"label": "Verse 2", "line_count": 3},
        "first\nsecond\nthird",
    )
    assert lines == ["first", "second", "third"]


def test_lyrics_generation_options_uses_defaults_and_cjk_repeat_penalty():
    options = audio_planner._lyrics_generation_options({}, _prompt_plan(language="ja"))
    assert options["temperature"] == 0.1
    assert options["top_p"] == 0.8
    assert options["repeat_penalty"] == 1.18


def test_lyrics_generation_options_allows_config_override():
    options = audio_planner._lyrics_generation_options(
        {"integrations": {"ollama_lyrics_options": {"temperature": 0.3, "top_p": 0.9, "repeat_penalty": 1.25}}},
        _prompt_plan(language="en"),
    )
    assert options == {"temperature": 0.3, "top_p": 0.9, "repeat_penalty": 1.25}
