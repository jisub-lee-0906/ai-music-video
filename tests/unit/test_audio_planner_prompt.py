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
    assert "line_count must be the exact number of sung lyric lines wanted for that block" in prompt
    assert "AceStep tags text field" in prompt
    assert "Keep fields separated" in prompt
    assert "Do not put planning notes, camera language, or placeholders inside labels or style fields" in prompt
    assert "Audio intent=mature female vocal, glossy piano, disco bounce." in prompt
    assert "World intent=warm urban nightlife." in prompt
    assert "Hook intent=neon rain and chrome reflections." in prompt
    assert "Story world=retro city-pop lane." in prompt
    assert "Avoid=no futuristic sci-fi tone." in prompt
    assert "Do not make Verse 2 feel like a copy-paste replay of Verse 1" in prompt
    assert "Only use post_chorus when the hook benefits from one extra tag" in prompt
    assert "Make the final chorus unmistakably bigger or more complete than earlier choruses" in prompt


def test_audio_outline_prompt_keeps_language_direction():
    prompt = audio_planner._audio_prompt(_prompt_plan())
    assert "Lyrics language=ja." in prompt
    assert "Write fluent modern Japanese lyrics" in prompt
    assert "Keep phrasing natural and singable" in prompt
    assert "Use English sparingly and intentionally" in prompt
    assert "Do not invent unreadable compounds, corrupted glyph strings, or mixed-script noise" in prompt


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
    assert "Write plain text only. Do not output JSON." in prompt
    assert "For each block, write the label in square brackets on its own line" in prompt
    assert "Keep the block order exactly the same as the outline." in prompt


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
                {"section": "chorus", "label": "Chorus", "style": "lift", "lines": ["夜のままそばにいて"]},
                {"section": "chorus", "label": "Final Chorus", "style": "peak", "lines": ["夜のままもう一度そばにいて"]},
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
        lambda _config, _prompt, **_kwargs: "[Verse 1]\na\nb\nc\nd",
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


def test_normalize_and_validate_keeps_llm_duration_when_not_overridden(monkeypatch):
    monkeypatch.setattr(
        audio_planner,
        "_plan_with_llm",
        lambda _config, _plan: {
            "genre_description": "Japanese city pop: glossy electric piano",
            "bpm": 120,
            "keyscale": "",
            "seed": 31,
            "duration": 999,
            "lyrics_blocks": [
                {"section": "intro", "label": "Intro", "style": "set", "lines": ["夜風が鳴る"]},
                {"section": "verse_1", "label": "Verse 1", "style": "move", "lines": ["改札を抜ける"]},
                {"section": "chorus", "label": "Final Chorus", "style": "peak", "lines": ["青い光へ"]},
                {"section": "outro", "label": "Outro", "style": "land", "lines": ["まだ消えない"]},
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


def test_merge_audio_outline_and_lyrics_requires_exact_locked_structure():
    merged = audio_planner._merge_audio_outline_and_lyrics(
        {
            "genre_description": "brief",
            "bpm": 100,
            "keyscale": "A major",
            "seed": 9,
            "duration": 180,
            "lyrics_blocks": [
                {"section": "intro", "label": "Intro", "style": "set", "line_count": 2},
            ],
        },
        {
            "lyrics_blocks": [
                {"section": "intro", "label": "Intro", "style": "set", "lines": ["a", "b"]},
            ]
        },
    )
    assert merged["lyrics_blocks"][0]["lines"] == ["a", "b"]


def test_parse_audio_lyrics_text_uses_label_headers_and_exact_line_counts():
    parsed = audio_planner._parse_audio_lyrics_text(
        {
            "lyrics_blocks": [
                {"section": "intro", "label": "Intro", "style": "set", "line_count": 1},
                {"section": "chorus", "label": "Final Chorus", "style": "peak", "line_count": 2},
            ]
        },
        "[Intro]\nfirst line\n\n[Final Chorus]\nsecond line\nthird line\n",
    )
    assert parsed["lyrics_blocks"][0]["lines"] == ["first line"]
    assert parsed["lyrics_blocks"][1]["lines"] == ["second line", "third line"]
