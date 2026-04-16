from ai_mv.core.planning.sections import merged_shot_section_type, normalized_sections


def test_sections_normalize_sort_and_clamp_rows():
    out = normalized_sections(
        {
            "sections": [
                {"name": "chorus", "start_sec": 10.0, "end_sec": 25.0},
                {"name": "intro", "start_sec": -1.0, "end_sec": 2.0},
                {"name": "verse", "start_sec": 2.0, "end_sec": 10.0},
            ]
        },
        20.0,
    )

    assert out[0]["section_type"] == "intro"
    assert out[0]["start_sec"] == 0.0
    assert out[-1]["end_sec"] == 20.0


def test_sections_merged_type_prefers_more_prominent_boundary():
    assert merged_shot_section_type({"section_type": "verse"}, {"section_type": "pre_chorus"}) == "pre_chorus"
    assert merged_shot_section_type({"section_type": "pre_chorus"}, {"section_type": "chorus"}) == "chorus"