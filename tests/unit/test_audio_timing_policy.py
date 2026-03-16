import ai_mv.core.orchestration.preflight as preflight_mod
from ai_mv.engines.acestep_1_5_aio.policy import audio_policy
from ai_mv.engines.acestep_1_5_aio.runner import _sections


def test_audio_policy_auto_duration_uses_bpm_and_default_songform_bars():
    out = audio_policy({"audio": {"bpm": 120}})
    assert out["duration"] == 200
    assert out["beats_per_bar"] == 4
    assert out["bar_lane"].startswith("intro 4")
    assert "final chorus 16" in out["bar_lane"]


def test_audio_policy_target_duration_override_wins():
    out = audio_policy({"audio": {"bpm": 108, "target_duration_sec": 180}})
    assert out["duration"] == 180
    assert out["duration_override"] is True


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


def test_sections_use_bar_ratio_not_line_weight():
    blocks = [
        {"section": "intro", "label": "Intro", "lines": ["a"]},
        {"section": "verse_1", "label": "Verse 1", "lines": ["b"]},
        {"section": "chorus", "label": "Chorus", "lines": ["c"]},
        {"section": "outro", "label": "Outro", "lines": ["d"]},
    ]
    out = _sections(80.0, blocks, 120, 4, {})
    assert out[0]["start_sec"] == 0.0
    assert out[0]["end_sec"] == 10.0
    assert out[1]["start_sec"] == 10.0
    assert out[1]["end_sec"] == 40.0
    assert out[2]["start_sec"] == 40.0
    assert out[2]["end_sec"] == 70.0
    assert out[3]["start_sec"] == 70.0
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
    audio_map = preflight_mod._preflight_audio_map(plan)
    assert audio_map["sections"][0]["end_sec"] == 8.889
    assert audio_map["sections"][1]["end_sec"] == 35.556
    assert audio_map["sections"][2]["start_sec"] == 35.556
