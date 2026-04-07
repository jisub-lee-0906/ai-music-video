import pytest

import ai_mv.engines.acestep_1_5_aio.planner as audio_planner


def _prompt_plan(**extra):
    plan = {
        "tags": "K-Pop, solo female, airy and emotional",
        "language": "ko",
        "genre_head": "K-Pop",
        "vocal_profile": "solo female",
        "vocal_tone": "airy and emotional",
        "audio_direction": "late-night breakup song that grows from restraint to direct release",
        "hook_direction": "short wet-city hook with a clear final lift",
        "hook_english_fragments": ["all night", "call my name"],
        "negative_direction": "avoid spectacle clutter",
        "duration": 150,
        "bpm": 108,
        "seed": 31,
        "quality": "high",
        "filename_prefix": "run_audio",
        "line_budgets": {
            "Intro": 0,
            "Verse 1": 4,
            "Verse 2": 4,
            "Pre-Chorus": 3,
            "Pre-Chorus 2": 3,
            "Chorus": 4,
            "Chorus 2": 4,
            "Final Chorus": 4,
            "Bridge": 2,
            "Outro": 0,
        },
        "terminal_end_tag": True,
        "final_chorus_required": True,
        "outro_required": False,
    }
    plan.update(extra)
    return plan


def test_audio_prompt_is_compact_and_keeps_core_contract():
    prompt = audio_planner._audio_prompt(_prompt_plan())
    assert "strict JSON only" in prompt
    assert "genre_description,bpm,keyscale,seed,duration,lyrics_blocks" in prompt
    assert "The final render format is [tags], then bracketed lyrics, then [Outro], then [end]" in prompt
    assert "genre_description is the future [tags] block" in prompt
    assert "core instruments, arrangement energy, and vocal character" in prompt
    assert "Prefer Verse 1 -> Pre-Chorus -> Chorus -> Verse 2 -> Pre-Chorus 2 -> Bridge -> Final Chorus" in prompt
    assert "director_brief_intent" not in prompt
    assert len(prompt) < 2600


def test_audio_prompt_uses_flattened_profile_fields():
    prompt = audio_planner._audio_prompt(_prompt_plan())
    assert "Audio intent=late-night breakup song that grows from restraint to direct release." in prompt
    assert "Hook intent=short wet-city hook with a clear final lift." in prompt
    assert "Genre=K-Pop." in prompt
    assert "Voice=solo female, airy and emotional." in prompt
    assert "Avoid=avoid spectacle clutter." in prompt
    assert "director_brief_intent" not in prompt


def test_audio_prompt_lets_llm_choose_bpm_when_unlocked():
    prompt = audio_planner._audio_prompt(_prompt_plan(bpm=0))
    assert "Target bpm is not fixed." in prompt
    assert "Choose it yourself from genre, songform, and breathing room." in prompt


def test_hook_scoring_prefers_world_anchored_korean_hook_over_generic_english():
    plan = _prompt_plan(hook_english_fragments=["all night", "call my name"])
    korean = {"fragment": "새벽 너머", "language_mode": "ko_only", "placement": "chorus"}
    english = {"fragment": "all night", "language_mode": "mixed_ko_en", "placement": "chorus"}
    assert audio_planner._score_hook_candidate(korean, plan) > audio_planner._score_hook_candidate(english, plan)


def test_build_audio_plan_accepts_minimal_profile_directly(monkeypatch):
    monkeypatch.setattr(
        audio_planner,
        "_plan_with_llm",
        lambda _config, _plan: {
            "genre_description": "K-Pop: glossy synth layers, tight electronic drums, and a solo female vocal with an airy emotional tone.",
            "bpm": 108,
            "keyscale": "A major",
            "seed": 31,
            "duration": 150,
            "lyrics_blocks": [
                {"section": "verse_1", "label": "Verse 1", "style": "restraint", "lines": ["젖은 불빛", "늦은 숨결", "비어 있는 길", "남은 이름"]},
                {"section": "pre_chorus", "label": "Pre-Chorus", "style": "tighten", "lines": ["더 가까워", "숨이 차올라", "문이 열린다"]},
                {"section": "chorus", "label": "Chorus", "style": "release", "lines": ["젖은 도시 끝", "나는 너를 봐", "꺼지지 않아", "끝내 나아가"]},
                {"section": "bridge", "label": "Bridge", "style": "reframe", "lines": ["멈춘 듯한 밤", "다시 숨을 쉬어"]},
                {"section": "chorus", "label": "Final Chorus", "style": "answer", "lines": ["젖은 도시 끝", "이제 나를 봐", "흔들리지 않아", "끝내 나아가"]},
            ],
        },
    )
    cfg = {
        "prompt": "late-night breakup song that grows from restraint to direct release",
        "genre": "k-pop synth pop",
        "voice": "solo female, airy and emotional",
        "language": "ko",
    }
    plan = audio_planner.build_audio_plan(cfg, {"run_id": "audio_test"})
    assert plan["language"] == "ko"
    assert plan["genre_head"] == "k-pop synth pop"
    assert plan["vocal_profile"] == "solo female"
    assert plan["vocal_tone"] == "airy and emotional"
    assert plan["audio_direction"] == "late-night breakup song that grows from restraint to direct release"
    assert plan["hook_direction"] == "late-night breakup song that grows from restraint to direct release"


def test_validate_outline_line_budgets_rejects_overpacked_blocks():
    with pytest.raises(RuntimeError, match="line_count too dense for Chorus"):
        audio_planner._validate_outline_line_budgets(
            {"line_budgets": {"Chorus": 6}},
            {"bpm": 108, "lyrics_blocks": [{"label": "Chorus", "line_count": 8}]},
        )


def test_generate_lyrics_block_skips_llm_for_zero_line_intro():
    block = {"section": "intro", "label": "Intro", "style": "open", "line_count": 0}
    out = audio_planner._generate_lyrics_block({}, _prompt_plan(), {"lyrics_blocks": [block]}, [], block)
    assert out["lines"] == []


def test_normalize_and_validate_keeps_llm_generated_bpm_and_keyscale(monkeypatch):
    monkeypatch.setattr(
        audio_planner,
        "_plan_with_llm",
        lambda _config, _plan: {
            "genre_description": "Rock: distorted electric guitars, punchy live drums, and a raw vocal that rises into a bigger hook.",
            "bpm": 146,
            "keyscale": "E minor",
            "seed": 31,
            "duration": 180,
            "lyrics_blocks": [
                {"section": "verse_1", "label": "Verse 1", "style": "drive", "lines": ["붉은 불꽃", "거친 숨결", "뜨거운 심장", "깨어난 밤"]},
                {"section": "pre_chorus", "label": "Pre-Chorus", "style": "lift", "lines": ["더 크게 울려", "멈추지 않아", "문을 열어"]},
                {"section": "chorus", "label": "Chorus", "style": "impact", "lines": ["지금 뛰어", "끝까지 가", "모든 걸 태워", "나를 외쳐"]},
                {"section": "bridge", "label": "Bridge", "style": "drop", "lines": ["정적이 와", "다시 깨어"]},
                {"section": "chorus", "label": "Final Chorus", "style": "impact", "lines": ["지금 뛰어", "두려움 없이", "벽을 넘어", "나를 외쳐"]},
            ],
        },
    )
    out = audio_planner._normalize_and_validate({}, _prompt_plan(bpm=108, keyscale="A major"))
    assert out["bpm"] == 146
    assert out["keyscale"] == "E minor"
