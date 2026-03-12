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
    assert "normal chorus should usually land in 6 lines" in prompt
    assert "Do not repeat the exact hook-anchor line again as line 3" in prompt
    assert "Do not reuse the exact hook-anchor line later in the same chorus block" in prompt
    assert "listener should feel progression from hook to answer to consequence" in prompt
    assert "The final chorus should usually open into 7 or 8 lines" in prompt
    assert "Post-chorus should usually stay at 2-3 short lines" in prompt
    assert "Outro should feel like a real landing" in prompt
    assert "Outro must not end on a bare noun fragment" in prompt
    assert "Bridge should feel like a real turn of the song" in prompt
    assert "At least half of the non-opening lines in the final chorus should differ" in prompt
    assert "The final chorus should contain one concrete visual or emotional payoff line" in prompt
    assert "would feel impossible or unearned earlier in the song" in prompt
    assert "Avoid fallback hook language like 'call my name'" in prompt
    assert "Avoid easy English callbacks like 'stay gold'" in prompt
    assert "generic English fragment" in prompt
    assert "The hook phrase should usually contain one concrete image" in prompt
    assert "genre_description must always be written in English" in prompt
    assert "Profile steering=retro city-pop lane." in prompt
    assert "Hook direction=neon rain and chrome reflections." in prompt
    assert "Preferred hook contour=" not in prompt
    assert "main chorus opening should be led by Japanese phrasing" in prompt
    assert "short English phrase become the emotional center" in prompt
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


def test_audio_plan_quality_rejects_weak_english_callback_for_japanese_song():
    plan = {
        "language": "ja",
        "lyrics_blocks": [
            {"section": "chorus", "label": "Chorus", "lines": ["濡れた街灯", "答えは遅い", "support one", "support two", "ほら stay gold, stay gold", "payoff"]},
            {"section": "chorus", "label": "Chorus 2", "lines": ["雨のガラス", "answer", "support one", "support two", "callback", "payoff"]},
            {"section": "chorus", "label": "Final Chorus", "lines": ["雨のガラス", "x", "y", "z", "u", "v", "w"]},
        ],
    }
    try:
        audio_planner._validate_audio_plan_quality(plan)
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert "weak english callback" in str(exc)


def test_audio_plan_quality_rejects_english_heavy_japanese_support_line():
    plan = {
        "language": "ja",
        "lyrics_blocks": [
            {"section": "chorus", "label": "Chorus", "lines": ["濡れた街灯", "答えは遅い", "support one", "the last ride you know", "callback", "payoff"]},
            {"section": "chorus", "label": "Chorus 2", "lines": ["雨のガラス", "answer", "support one", "support two", "callback", "payoff"]},
            {"section": "chorus", "label": "Final Chorus", "lines": ["雨のガラス", "x", "y", "z", "u", "v", "w"]},
        ],
    }
    try:
        audio_planner._validate_audio_plan_quality(plan)
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert "leans too heavily on English wording" in str(exc)


def test_audio_plan_quality_rejects_hook_anchor_repeated_as_line_three():
    plan = {
        "lyrics_blocks": [
            {"section": "chorus", "label": "Chorus", "lines": ["same", "tilt", "same", "d", "e", "f"]},
            {"section": "chorus", "label": "Chorus 2", "lines": ["a", "b", "c", "d", "e", "f"]},
            {"section": "chorus", "label": "Final Chorus", "lines": ["a", "x", "y", "z", "u", "v", "w"]},
        ]
    }
    try:
        audio_planner._validate_audio_plan_quality(plan)
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert "repeating the hook anchor too early" in str(exc)


def test_audio_candidate_scoring_penalizes_reused_hook_anchor():
    clean = {
        "lyrics_blocks": [
            {"section": "chorus", "label": "Chorus", "lines": ["same", "tilt", "rise", "move", "e", "f"]},
            {"section": "chorus", "label": "Chorus 2", "lines": ["a", "b", "c", "d", "e", "f"]},
            {"section": "chorus", "label": "Final Chorus", "lines": ["a", "x", "y", "z", "u", "v", "w", "q"]},
            {"section": "bridge", "label": "Bridge", "lines": ["もし離れても", "でも今夜は足りない", "あなたを選ぶ"]},
            {"section": "outro", "label": "Outro", "lines": ["wet glass fades", "the night settles by your side"]},
        ]
    }
    repeated = {
        "lyrics_blocks": [
            {"section": "chorus", "label": "Chorus", "lines": ["same", "tilt", "rise", "same", "e", "f"]},
            {"section": "chorus", "label": "Chorus 2", "lines": ["a", "b", "c", "d", "e", "f"]},
            {"section": "chorus", "label": "Final Chorus", "lines": ["a", "x", "y", "a", "u", "v", "w", "q"]},
            {"section": "bridge", "label": "Bridge", "lines": ["もし離れても", "でも今夜は足りない", "あなたを選ぶ"]},
            {"section": "outro", "label": "Outro", "lines": ["wet glass fades", "the night settles by your side"]},
        ]
    }
    assert audio_planner._score_hook_non_redundancy(clean) > audio_planner._score_hook_non_redundancy(repeated)


def test_audio_candidate_scoring_prefers_direct_hook_and_resolved_final_line():
    stronger = {
        "lyrics_blocks": [
            {"section": "chorus", "label": "Chorus", "lines": ["街灯の先へ", "b", "c", "d", "e", "f"]},
            {"section": "chorus", "label": "Final Chorus", "lines": ["街灯の先へ", "x", "y", "z", "u", "v", "w", "あなたと行ける"]},
        ]
    }
    weaker = {
        "lyrics_blocks": [
            {"section": "chorus", "label": "Chorus", "lines": ["街灯の余韻", "b", "c", "d", "e", "f"]},
            {"section": "chorus", "label": "Final Chorus", "lines": ["街灯の余韻", "x", "y", "z", "u", "v", "w", "朝まで"]},
        ]
    }
    assert audio_planner._score_hook_directness(stronger) > audio_planner._score_hook_directness(weaker)
    assert audio_planner._score_final_closure(stronger) > audio_planner._score_final_closure(weaker)


def test_audio_plan_quality_rejects_missing_support_payoff_lines():
    plan = {
        "lyrics_blocks": [
            {"section": "chorus", "label": "Chorus", "lines": ["same", "tilt", "hook echo", "tilt", "tilt", "tilt"]},
            {"section": "chorus", "label": "Chorus 2", "lines": ["a", "b", "c", "d", "e", "f"]},
            {"section": "chorus", "label": "Final Chorus", "lines": ["a", "x", "y", "z", "u", "v", "w"]},
        ]
    }
    try:
        audio_planner._validate_audio_plan_quality(plan)
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert "chorus lacks support or payoff lines" in str(exc)


def test_audio_plan_quality_rejects_too_short_first_chorus():
    plan = {
        "lyrics_blocks": [
            {"section": "chorus", "label": "Chorus", "lines": ["a", "b", "c", "d", "e"]},
            {"section": "chorus", "label": "Chorus 2", "lines": ["a", "b", "c", "d", "e", "f"]},
            {"section": "chorus", "label": "Final Chorus", "lines": ["a", "x", "y", "z", "u", "v", "w"]},
        ]
    }
    try:
        audio_planner._validate_audio_plan_quality(plan)
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert "first chorus too short" in str(exc)


def test_audio_plan_quality_rejects_weak_post_chorus():
    plan = {
        "lyrics_blocks": [
            {"section": "chorus", "label": "Chorus", "lines": ["rain street", "answer line", "support one", "support two", "callback", "payoff"]},
            {"section": "post_chorus", "label": "Post-Chorus", "lines": ["tiny", "bits"]},
            {"section": "chorus", "label": "Chorus 2", "lines": ["rain street", "b", "c", "d", "e", "f"]},
            {"section": "chorus", "label": "Final Chorus", "lines": ["rain street", "x", "y", "z", "u", "v", "w"]},
        ]
    }
    try:
        audio_planner._validate_audio_plan_quality(plan)
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert "post-chorus" in str(exc)


def test_audio_plan_quality_rejects_too_short_final_chorus():
    plan = {
        "lyrics_blocks": [
            {"section": "chorus", "label": "Chorus", "lines": ["rain street", "answer", "support one", "support two", "callback", "payoff"]},
            {"section": "chorus", "label": "Chorus 2", "lines": ["rain street", "new answer", "support one", "support two", "callback", "payoff"]},
            {"section": "chorus", "label": "Final Chorus", "lines": ["rain street", "x", "y", "z", "u", "v"]},
        ]
    }
    try:
        audio_planner._validate_audio_plan_quality(plan)
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert "final chorus too short" in str(exc)


def test_audio_plan_quality_rejects_fragmentary_outro_ending():
    plan = {
        "lyrics_blocks": [
            {"section": "chorus", "label": "Chorus", "lines": ["rain street", "answer", "support one", "support two", "callback", "payoff"]},
            {"section": "chorus", "label": "Chorus 2", "lines": ["rain street", "new answer", "support one", "support two", "callback", "payoff"]},
            {"section": "chorus", "label": "Final Chorus", "lines": ["rain street", "x", "y", "z", "u", "v", "w"]},
            {"section": "outro", "label": "Outro", "lines": ["wet glass fades", "アフターグロウ"]},
        ]
    }
    try:
        audio_planner._validate_audio_plan_quality(plan)
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert "outro ending feels too fragmentary" in str(exc)


def test_audio_plan_quality_rejects_bridge_without_turn():
    plan = {
        "lyrics_blocks": [
            {"section": "chorus", "label": "Chorus", "lines": ["rain street", "answer", "support one", "support two", "callback", "payoff"]},
            {"section": "chorus", "label": "Chorus 2", "lines": ["rain street", "new answer", "support one", "support two", "callback", "payoff"]},
            {"section": "bridge", "label": "Bridge", "lines": ["the station glows softly", "wet glass keeps shining", "night air drifts slowly"]},
            {"section": "chorus", "label": "Final Chorus", "lines": ["rain street", "x", "y", "z", "u", "v", "w"]},
            {"section": "outro", "label": "Outro", "lines": ["wet glass fades", "the night settles by your side"]},
        ]
    }
    try:
        audio_planner._validate_audio_plan_quality(plan)
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert "bridge lacks a real emotional turn" in str(exc)


def test_audio_plan_quality_rejects_final_chorus_that_does_not_answer_bridge():
    plan = {
        "lyrics_blocks": [
            {"section": "chorus", "label": "Chorus", "lines": ["rain street", "answer", "support one", "support two", "callback", "payoff"]},
            {"section": "chorus", "label": "Chorus 2", "lines": ["rain street", "new answer", "support one", "support two", "callback", "payoff"]},
            {"section": "bridge", "label": "Bridge", "lines": ["もし離れても", "背中を向けても", "だから今だけ選びたい"]},
            {"section": "chorus", "label": "Final Chorus", "lines": ["rain street", "x", "y", "z", "u", "v", "w"]},
            {"section": "outro", "label": "Outro", "lines": ["wet glass fades", "the night settles by your side"]},
        ]
    }
    try:
        audio_planner._validate_audio_plan_quality(plan)
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert "does not answer the bridge strongly enough" in str(exc)


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


def test_audio_plan_quality_rejects_awkward_japanese_english_center_line():
    plan = {
        "language": "ja",
        "lyrics_blocks": [
            {"section": "chorus", "label": "Chorus", "lines": ["濡れた街灯", "返事はまだ遅い", "雨粒が肩をなぞる", "ねえ Last ride 逃さないで", "そのまま見つめて", "街がまた揺れる"]},
            {"section": "chorus", "label": "Chorus 2", "lines": ["濡れた街灯が揺れてる", "横顔だけが近くなる", "雨粒が肩をなぞる", "最後の電車がにじむ", "そのまま見つめて", "街がまた揺れる"]},
            {"section": "chorus", "label": "Final Chorus", "lines": ["濡れた街灯が揺れてる", "今夜はちゃんと届いてる", "ガラスの向こうで息をする", "終電のベルも遠くなる", "そのまま見つめて", "街がまたほどける", "濡れたホームに熱が残る"]},
        ],
    }
    try:
        audio_planner._validate_audio_plan_quality(plan)
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert "short English phrase dominate too directly" in str(exc)


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


def test_plan_with_quality_attempts_selects_best_passing_candidate(monkeypatch):
    def fake_normalize(_config, attempt_plan):
        return {"candidate": attempt_plan["seed"]}

    def fake_score(plan):
        return 1 if plan["candidate"] == 31 else 9

    monkeypatch.setattr(audio_planner, "_normalize_and_validate", fake_normalize)
    monkeypatch.setattr(audio_planner, "_score_audio_candidate", fake_score)
    result = audio_planner._plan_with_quality_attempts(
        {"audio": {"planner_attempts": 2}},
        {"seed": 31, "language": "ja"},
    )
    assert result["candidate"] == 1040
