import ai_mv.engines.acestep_1_5_split.planner as audio_planner


def test_audio_prompt_requires_final_return_after_bridge():
    prompt = audio_planner._audio_prompt(
        {
            "tags": "city pop, neon",
            "style_guidance": "night drive romance",
            "language": "ja",
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
    assert "genre_description must always be written in English" in prompt
    assert "Profile steering=retro city-pop lane." in prompt
    assert "Hook direction=neon rain and chrome reflections." in prompt
    assert "Preferred hook contour=" not in prompt
    assert "main chorus opening should be led by Japanese phrasing" in prompt
    assert "Make the chorus opening feel like a plausible song title" in prompt
    assert "title-worthiness" in prompt


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


def test_audio_plan_quality_rejects_english_heavy_japanese_hook_anchor():
    plan = {
        "language": "ja",
        "lyrics_blocks": [
            {"section": "chorus", "label": "Chorus", "lines": ["濡れた街灯 light me up", "返事はまだ遅い", "雨粒が肩をなぞる", "最後の電車がにじむ", "そのまま見つめて", "街がまた揺れる"]},
            {"section": "chorus", "label": "Chorus 2", "lines": ["濡れた街灯が揺れてる", "横顔だけが近くなる", "雨粒が肩をなぞる", "最後の電車がにじむ", "そのまま見つめて", "街がまた揺れる"]},
            {"section": "chorus", "label": "Final Chorus", "lines": ["濡れた街灯が揺れてる", "今夜はちゃんと届いてる", "ガラスの向こうで息をする", "終電のベルも遠くなる", "そのまま見つめて", "街がまたほどける", "濡れたホームに熱が残る"]},
        ],
    }
    try:
        audio_planner._validate_audio_plan_quality(plan)
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert "leans too heavily on English fragment" in str(exc)


def test_audio_plan_quality_rejects_hook_without_concrete_world_anchor():
    plan = {
        "language": "ja",
        "hook_direction": "濡れたガラス, 街灯, ラストライド",
        "profile_summary": "夜の街の反射と余熱",
        "lyrics_blocks": [
            {"section": "chorus", "label": "Chorus", "lines": ["この恋は消えない", "返事はまだ遅い", "雨粒が肩をなぞる", "最後の電車がにじむ", "そのまま見つめて", "街がまた揺れる"]},
            {"section": "chorus", "label": "Chorus 2", "lines": ["濡れたガラスがほどける", "横顔だけが近くなる", "雨粒が肩をなぞる", "最後の電車がにじむ", "そのまま見つめて", "街がまた揺れる"]},
            {"section": "chorus", "label": "Final Chorus", "lines": ["濡れたガラスがほどける", "今夜はちゃんと届いてる", "ガラスの向こうで息をする", "終電のベルも遠くなる", "そのまま見つめて", "街がまたほどける", "濡れたホームに熱が残る"]},
        ],
    }
    try:
        audio_planner._validate_audio_plan_quality(plan)
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert "lacks a concrete world anchor" in str(exc)


def test_audio_plan_quality_rejects_weak_japanese_hook_opening():
    plan = {
        "language": "ja",
        "hook_direction": "濡れたガラス, 街灯, ラストライド",
        "profile_summary": "夜の街の反射と余熱",
        "lyrics_blocks": [
            {"section": "chorus", "label": "Chorus", "lines": ["濡れた街灯　まだ揺れてる", "返事はまだ遅い", "雨粒が肩をなぞる", "最後の電車がにじむ", "そのまま見つめて", "街がまた揺れる"]},
            {"section": "chorus", "label": "Chorus 2", "lines": ["街灯のリフレイン　まだ熱い", "横顔だけが近くなる", "雨粒が肩をなぞる", "最後の電車がにじむ", "そのまま見つめて", "街がまた揺れる"]},
            {"section": "chorus", "label": "Final Chorus", "lines": ["街灯のリフレイン　まだ熱い", "今夜はちゃんと届いてる", "ガラスの向こうで息をする", "終電のベルも遠くなる", "そのまま見つめて", "街がまたほどける", "濡れたホームに熱が残る"]},
        ],
    }
    try:
        audio_planner._validate_audio_plan_quality(plan)
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert "feels too generic" in str(exc)


def test_attempt_plan_adds_hook_shape_bias():
    attempt = audio_planner._attempt_plan({"seed": 31, "language": "ja"}, 1)
    assert attempt["seed"] == 1040
    assert attempt["hook_shape_bias"]
    prompt = audio_planner._audio_prompt(
        {
            "tags": "city pop, neon",
            "style_guidance": "night drive romance",
            "language": "ja",
            "profile_summary": "retro city-pop lane",
            "audio_direction": "mature female vocal, glossy piano, disco bounce",
            "hook_direction": "neon rain and chrome reflections",
            "visual_direction": "warm urban nightlife",
            "negative_direction": "no futuristic sci-fi tone",
            "duration": 200,
            "bpm": 108,
            "hook_shape_bias": attempt["hook_shape_bias"],
        }
    )
    assert "Preferred hook contour=" in prompt
