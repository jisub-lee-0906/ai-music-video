from ai_mv.core.stages.acestep_music import build_audio_preview_map
from ai_mv.engines.acestep_1_5_aio.policy import audio_policy
from ai_mv.engines.acestep_1_5_aio.runner import _sections


def test_audio_policy_leaves_duration_open_without_explicit_target():
    out = audio_policy({"audio": {"bpm": 120}})
    assert out["duration"] == 0
    assert out["beats_per_bar"] == 4
    assert out["bar_lane"].startswith("intro 8")
    assert "final chorus 16" in out["bar_lane"]
    assert out["duration_min_sec"] == 150
    assert out["duration_max_sec"] == 180


def test_audio_policy_target_duration_override_wins():
    out = audio_policy({"audio": {"bpm": 108, "target_duration_sec": 180}})
    assert out["duration"] == 180
    assert out["duration_override"] is True


def test_audio_policy_uses_compact_songlet_contract_for_thirty_second_validation():
    out = audio_policy({"audio": {"bpm": 118, "target_duration_min_sec": 25, "target_duration_max_sec": 35}})

    assert out["songform_mode"] == "hook_validation"
    assert out["section_bars"]["intro"] == 4
    assert out["section_bars"]["verse_1"] == 0
    assert out["section_bars"]["pre_chorus"] == 0
    assert out["section_bars"]["chorus"] == 8
    assert out["section_bars"]["final_chorus_bonus"] == 0
    assert out["line_budgets"]["Verse 1"] == 0
    assert out["line_budgets"]["Pre-Chorus"] == 0
    assert out["line_budgets"]["Chorus"] == 2
    assert [row["label"] for row in out["songform_variants"][0]] == ["Intro", "Chorus", "Outro"]
    assert "verse 1" not in out["bar_lane"].lower()
    assert "pre" not in out["bar_lane"].lower()
    assert "chorus 8" in out["bar_lane"]


def test_audio_policy_populates_default_ending_contract():
    out = audio_policy({"audio": {"bpm": 108, "language": "ko"}})
    assert out["ending_mode"] == "clean_resolve"
    assert out["terminal_end_tag"] is True
    assert out["final_chorus_required"] is False
    assert out["outro_required"] is False
    assert out["ending_vocal_density"] == "medium"
    assert "clean ending" in out["ending_tags"]
    assert out["line_budgets"]["Intro"] == 0
    assert out["line_budgets"]["Verse 1"] == 4
    assert out["line_budgets"]["Pre-Chorus"] == 3
    assert out["line_budgets"]["Final Chorus"] == 5

    assert out["line_budgets"]["Outro"] == 0


def test_audio_policy_keeps_intro_and_outro_instrumental_by_default():
    out = audio_policy(
        {
            "audio": {
                "bpm": 108,
                "ending_mode": "clean_resolve",
                "outro_required": True,
                "ending_vocal_density": "low",
                "terminal_end_tag": True,
                "language": "ko",
            }
        }
    )
    assert out["line_budgets"]["Intro"] == 0
    assert out["line_budgets"]["Outro"] == 0


def test_audio_policy_accepts_custom_section_bars():
    out = audio_policy(
        {
            "audio": {
                "bpm": 120,
                "section_bars": {
                    "verse": 8,
                    "chorus": 8,
                    "final_chorus_bonus": 8,
                },
            }
        }
    )
    assert out["section_bars"]["verse"] == 8
    assert out["section_bars"]["chorus"] == 8
    assert out["section_bars"]["final_chorus_bonus"] == 8


def test_audio_policy_rejects_non_multiple_of_four_section_bars():
    try:
        audio_policy({"audio": {"section_bars": {"pre_chorus": 6}}})
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert "multiple of 4" in str(exc)


def test_sections_use_bar_ratio_not_line_weight():
    blocks = [
        {"section": "intro", "label": "Intro", "lines": ["a"]},
        {"section": "verse_1", "label": "Verse 1", "lines": ["b"]},
        {"section": "chorus", "label": "Chorus", "lines": ["c"]},
        {"section": "outro", "label": "Outro", "lines": ["d"]},
    ]
    out = _sections(80.0, blocks, 120, 4, {})
    assert out[0]["start_sec"] == 0.0
    assert out[0]["end_sec"] == 20.0
    assert out[1]["start_sec"] == 20.0
    assert out[1]["end_sec"] == 40.0
    assert out[2]["start_sec"] == 40.0
    assert out[2]["end_sec"] == 60.0
    assert out[3]["start_sec"] == 60.0
    assert out[3]["end_sec"] == 80.0


def test_preflight_audio_map_uses_same_bar_timing_policy():
    plan = {
        "duration": 80,
        "bpm": 120,
        "beats_per_bar": 4,
        "section_bars": {},
        "lyrics_blocks": [
            {"section": "intro", "label": "Intro", "lines": ["a"]},
            {"section": "verse_1", "label": "Verse 1", "lines": ["b"]},
            {"section": "chorus", "label": "Final Chorus", "lines": ["c"]},
            {"section": "outro", "label": "Outro", "lines": ["d"]},
        ],
    }
    audio_map = build_audio_preview_map(plan)
    assert audio_map["sections"][0]["end_sec"] == 16.0
    assert audio_map["sections"][1]["end_sec"] == 32.0
    assert audio_map["sections"][2]["start_sec"] == 32.0
