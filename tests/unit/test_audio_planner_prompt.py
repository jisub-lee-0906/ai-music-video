import pytest

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
        "line_budgets": {
            "Intro": 1,
            "Verse 1": 4,
            "Verse 2": 4,
            "Pre-Chorus": 3,
            "Pre-Chorus 2": 3,
            "Chorus": 4,
            "Chorus 2": 4,
            "Final Chorus": 4,
            "Bridge": 2,
            "Outro": 1,
        },
    }
    plan.update(extra)
    return plan


def test_audio_prompt_focuses_on_outline_planning_not_lyrics_dump():
    prompt = audio_planner._audio_prompt(_prompt_plan())
    assert "Return JSON only" in prompt
    assert "Allowed section values only" in prompt
    assert "For this planning step, do not write lyric lines yet" in prompt
    assert "Do not make Verse 2 feel like a copy-paste replay of Verse 1" in prompt
    assert "compact English production brief" in prompt
    assert "Do not rely on artist-name shorthand" in prompt
    assert "Protect vocal breathing room" in prompt
    assert "Final Chorus<= 4 lines" in prompt
    assert "final [End] marker" in prompt
    assert "instrumental-friendly by default" in prompt


def test_audio_outline_prompt_keeps_language_direction():
    prompt = audio_planner._audio_prompt(_prompt_plan())
    assert "Lyrics language=ko." in prompt
    assert "Write fluent modern Korean lyrics" in prompt
    assert "canonical English section labels exactly as provided in the outline" in prompt
    assert "Character identity=Korean female idol in her twenties." in prompt
    assert "future bracketed lyric markup skeleton" in prompt


def test_build_audio_plan_exposes_direction_fields_and_ending_contract():
    config = {
        "audio": {
            "language": "ko",
            "genre_head": "K-Pop",
            "vocal_profile": "female lead vocal",
            "vocal_tone": "airy and youthful",
            "ending_mode": "clean_resolve",
            "outro_required": True,
            "ending_vocal_density": "low",
            "section_bars": {"outro": 2},
            "brief": "glossy synth-pop with a bright but emotional lead vocal",
            "hook_brief": "a title-worthy hook with a clean final lift",
            "bpm": 118,
        },
        "visual": {
            "story_premise": "A heroine crosses one connected city night.",
            "world_rules": "Late-night station streets stay continuous and grounded.",
            "heroine_arc": "She grows clearer as she moves forward.",
            "forbidden_story_moves": "Avoid surreal spectacle and random sci-fi drift.",
        },
        "character": {
            "identity_core": "Korean female idol in her twenties",
            "anchor_wardrobe_guidance": "polished off-duty idol silhouette",
        },
    }
    plan = audio_planner.build_audio_plan(config, {"run_id": "audio_test"})
    assert plan["audio_direction"] == "glossy synth-pop with a bright but emotional lead vocal"
    assert plan["hook_direction"] == "a title-worthy hook with a clean final lift"
    assert "random sci-fi drift" in plan["negative_direction"]
    assert plan["genre_head"] == "K-Pop"
    assert plan["vocal_profile"] == "female lead vocal"
    assert plan["vocal_tone"] == "airy and youthful"
    assert plan["ending_mode"] == "clean_resolve"
    assert plan["terminal_end_tag"] is True
    assert plan["final_chorus_required"] is True
    assert plan["outro_required"] is True
    assert plan["ending_vocal_density"] == "low"
    assert plan["section_bars"]["outro"] == 2
    assert plan["line_budgets"]["Intro"] == 1
    assert plan["line_budgets"]["Outro"] == 1
    assert plan["line_budgets"]["Verse 1"] == 4
    assert plan["line_budgets"]["Final Chorus"] == 4


def test_audio_intent_clause_dedupes_world_and_avoid_text():
    prompt = audio_planner._audio_prompt(
        _prompt_plan(
            director_brief_intent={
                "audio_brief": "glossy pop production with late-night momentum.",
                "audio_hook_brief": "rain-light hook with a clean forward lift.",
                "visual_brief": "cinematic city-night movement.",
                "story_world": "late-night transit spaces and wet street reflections.",
                "world_core": "late-night transit spaces and wet street reflections.",
                "payoff_style": "",
                "outro_feel": "",
                "identity_core": "Korean female idol in her twenties.",
                "visual_negative": "avoid spectacle clutter.",
                "avoid": "avoid spectacle clutter.",
            }
        )
    )
    assert prompt.count("Story world=") == 1
    assert "World core=" not in prompt
    assert prompt.count("Avoid=avoid spectacle clutter.") == 1


def test_validate_outline_line_budgets_rejects_overpacked_blocks():
    with pytest.raises(RuntimeError, match="line_count too dense for Chorus"):
        audio_planner._validate_outline_line_budgets(
            {"line_budgets": {"Chorus": 6}},
            {"lyrics_blocks": [{"label": "Chorus", "line_count": 8}]},
        )


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
