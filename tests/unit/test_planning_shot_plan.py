from ai_mv.core.planning.shot_plan import build_shot_plan


def test_shot_plan_adds_shot_intent_fields():
    out = build_shot_plan(
        {"planning": {"max_shot_sec": 8.0}},
        [
            {
                "index": 1,
                "section_name": "VERSE 1",
                "section_type": "verse",
                "start_sec": 0.0,
                "end_sec": 8.0,
                "duration_sec": 8.0,
            },
            {
                "index": 2,
                "section_name": "CHORUS",
                "section_type": "chorus",
                "start_sec": 8.0,
                "end_sec": 14.0,
                "duration_sec": 6.0,
            },
        ],
        style_name="citypop",
    )

    verse_shot = next(shot for shot in out if shot["section_type"] == "verse")
    chorus_shot = next(shot for shot in out if shot["section_type"] == "chorus")

    assert verse_shot["edit_role"] == "support"
    assert verse_shot["coverage_role"] == "connective"
    assert verse_shot["workflow_intent"] == "stable_i2v"
    assert verse_shot["framing_intent"] == "hero_medium"
    assert chorus_shot["edit_role"] == "hook"
    assert chorus_shot["coverage_role"] == "anchor"
    assert chorus_shot["workflow_intent"] == "audio_reactive_candidate"
    assert chorus_shot["framing_intent"] == "performance_closeup"


def test_shot_plan_gives_long_chorus_a_non_close_support_shot():
    out = build_shot_plan(
        {"planning": {"max_shot_sec": 8.0}},
        [
            {
                "index": 1,
                "section_name": "CHORUS",
                "section_type": "chorus",
                "start_sec": 0.0,
                "end_sec": 8.0,
                "duration_sec": 8.0,
            },
        ],
        style_name="citypop",
    )

    assert len(out) == 2
    anchor = out[0]
    support = out[1]
    assert anchor["visual_mode"] == "chorus_performance"
    assert anchor["coverage_role"] == "anchor"
    assert anchor["framing_intent"] == "performance_closeup"
    assert support["visual_mode"] == "neon_release"
    assert support["coverage_role"] == "connective"
    assert support["framing_intent"] == "release_wide"


def test_shot_plan_builds_renumbered_shots_from_sections():
    out = build_shot_plan(
        {"planning": {"max_shot_sec": 8.0}},
        [
            {
                "index": 1,
                "section_name": "VERSE 1",
                "section_type": "verse",
                "start_sec": 0.0,
                "end_sec": 8.0,
                "duration_sec": 8.0,
            },
            {
                "index": 2,
                "section_name": "CHORUS",
                "section_type": "chorus",
                "start_sec": 8.0,
                "end_sec": 14.0,
                "duration_sec": 6.0,
            },
        ],
        style_name="citypop",
    )

    assert out[0]["shot_id"] == "S001"
    assert any(shot["section_type"] == "chorus" for shot in out)
    assert any(shot["visual_mode"] == "rain_window_detail" for shot in out if shot["section_type"] == "verse")


def test_shot_plan_splits_oversized_parts_using_max_shot_sec():
    out = build_shot_plan(
        {"planning": {"max_shot_sec": 4.0}},
        [
            {
                "index": 1,
                "section_name": "VERSE 1",
                "section_type": "verse",
                "start_sec": 0.0,
                "end_sec": 10.0,
                "duration_sec": 10.0,
            }
        ],
        style_name="citypop",
    )

    assert len(out) >= 3
    assert all(float(shot["duration_sec"]) <= 4.0 for shot in out)


def test_shot_plan_rejects_unknown_style_name():
    import pytest

    with pytest.raises(KeyError):
        build_shot_plan(
            {"planning": {"max_shot_sec": 8.0}},
            [
                {
                    "index": 1,
                    "section_name": "VERSE 1",
                    "section_type": "verse",
                    "start_sec": 0.0,
                    "end_sec": 8.0,
                    "duration_sec": 8.0,
                }
            ],
            style_name="unknown-style",
        )
