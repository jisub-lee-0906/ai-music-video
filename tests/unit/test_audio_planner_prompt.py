import ai_mv.engines.acestep_1_5_aio.planner as audio_planner


def _prompt_plan(**extra):
    plan = {
        "tags": "cinematic pop, female vocal",
        "language": "ko",
        "director_brief_intent": {
            "audio_brief": "glossy pop production with late-night momentum",
            "audio_hook_brief": "rain-light hook with a clean forward lift",
            "visual_brief": "cinematic city-night movement",
            "story_world": "late-night transit spaces and wet street reflections",
            "world_core": "one connected city night with reflective thresholds",
            "payoff_style": "open the world on the final return",
            "outro_feel": "leave a controlled after-image",
            "identity_core": "Korean female idol in her twenties",
            "visual_negative": "avoid spectacle clutter",
            "avoid": "random sci-fi drift",
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
    assert "Do not make Verse 2 feel like a copy-paste replay of Verse 1" in prompt


def test_audio_outline_prompt_keeps_language_direction():
    prompt = audio_planner._audio_prompt(_prompt_plan())
    assert "Lyrics language=ko." in prompt
    assert "Write fluent modern Korean lyrics" in prompt
    assert "canonical English section labels exactly as provided in the outline" in prompt
    assert "Character identity=Korean female idol in her twenties." in prompt


def test_plan_lyrics_with_llm_uses_codex_text_generation(monkeypatch):
    monkeypatch.setattr(
        audio_planner,
        "generate_text",
        lambda _config, _prompt, **_kwargs: "a\nb\nc\nd",
    )
    merged = audio_planner._plan_lyrics_with_llm(
        {},
        _prompt_plan(),
        {
            "genre_description": "cinematic pop: glossy synths",
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
