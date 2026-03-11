import ai_mv.engines.acestep_1_5_split.planner as audio_planner


def test_audio_prompt_requires_final_return_after_bridge():
    prompt = audio_planner._audio_prompt(
        {
            "tags": "city pop, neon",
            "style_guidance": "night drive romance",
            "profile_summary": "retro city-pop lane",
            "audio_direction": "mature female vocal, glossy piano, disco bounce",
            "hook_direction": "neon rain and chrome reflections",
            "visual_direction": "warm urban nightlife",
            "negative_direction": "no futuristic sci-fi tone",
            "duration": 200,
            "bpm": 108,
        }
    )
    assert "A bridge must never be the final large section" in prompt
    assert "label the last one as Final Chorus" in prompt
    assert "Aim for 9-11 lyrics_blocks" in prompt
    assert "change at least one support line" in prompt
    assert "Do not repeat the exact same six chorus lines three times" in prompt
    assert "do not copy the opening line verbatim into line two" in prompt
    assert "line 1 should act as the hook anchor" in prompt
    assert "At least half of the non-opening lines in the final chorus should differ" in prompt
    assert "The final chorus should contain one concrete visual or emotional payoff line" in prompt
    assert "Avoid fallback hook language like 'call my name'" in prompt
    assert "generic English fragment" in prompt
    assert "The hook phrase should usually contain one concrete image" in prompt
    assert "Profile steering=retro city-pop lane." in prompt
    assert "Hook direction=neon rain and chrome reflections." in prompt


def test_audio_plan_quality_rejects_duplicate_second_chorus():
    plan = {
        "lyrics_blocks": [
            {"section": "chorus", "label": "Chorus", "lines": ["a", "b", "c", "d", "e", "f"]},
            {"section": "chorus", "label": "Chorus 2", "lines": ["a", "b", "c", "d", "e", "f"]},
            {"section": "chorus", "label": "Final Chorus", "lines": ["a", "x", "y", "z", "u", "v", "w"]},
        ]
    }
    try:
        audio_planner._validate_audio_plan_quality(plan)
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert "second chorus duplicates first chorus exactly" in str(exc)


def test_audio_plan_quality_rejects_duplicated_chorus_opening_pair():
    plan = {
        "lyrics_blocks": [
            {"section": "chorus", "label": "Chorus", "lines": ["same", "same", "c", "d", "e", "f"]},
            {"section": "chorus", "label": "Chorus 2", "lines": ["a", "b", "c", "d", "e", "f"]},
            {"section": "chorus", "label": "Final Chorus", "lines": ["a", "x", "y", "z", "u", "v", "w"]},
        ]
    }
    try:
        audio_planner._validate_audio_plan_quality(plan)
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert "chorus opening pair duplicates verbatim" in str(exc)


def test_audio_plan_quality_rejects_generic_hook_fragment():
    plan = {
        "lyrics_blocks": [
            {"section": "chorus", "label": "Chorus", "lines": ["rain street", "look at me", "c", "d", "e", "f"]},
            {"section": "chorus", "label": "Chorus 2", "lines": ["a", "b", "c", "d", "e", "f"]},
            {"section": "chorus", "label": "Final Chorus", "lines": ["a", "x", "y", "z", "u", "v", "w"]},
        ]
    }
    try:
        audio_planner._validate_audio_plan_quality(plan)
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert "generic hook fragment" in str(exc)


def test_audio_plan_quality_rejects_overrepeated_chorus_anchor():
    plan = {
        "lyrics_blocks": [
            {"section": "chorus", "label": "Chorus", "lines": ["same", "tilt", "same", "same", "x", "y"]},
            {"section": "chorus", "label": "Chorus 2", "lines": ["a", "b", "c", "d", "e", "f"]},
            {"section": "chorus", "label": "Final Chorus", "lines": ["a", "x", "y", "z", "u", "v", "w"]},
        ]
    }
    try:
        audio_planner._validate_audio_plan_quality(plan)
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert "chorus anchor repeated too many times" in str(exc)


def test_audio_plan_quality_rejects_missing_support_payoff_lines():
    plan = {
        "lyrics_blocks": [
            {"section": "chorus", "label": "Chorus", "lines": ["same", "tilt", "same", "tilt", "tilt", "same-ish"]},
            {"section": "chorus", "label": "Chorus 2", "lines": ["a", "b", "c", "d", "e", "f"]},
            {"section": "chorus", "label": "Final Chorus", "lines": ["a", "x", "y", "z", "u", "v", "w"]},
        ]
    }
    try:
        audio_planner._validate_audio_plan_quality(plan)
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert "chorus lacks support or payoff lines" in str(exc)
