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



def test_sections_emit_source_label_and_normalization_confidence_metadata():
    out = normalized_sections(
        {
            "sections": [
                {"name": "Hook 1", "start_sec": 0.0, "end_sec": 6.0},
                {"name": "Middle 8", "start_sec": 6.0, "end_sec": 10.0},
                {"name": "Solo", "start_sec": 10.0, "end_sec": 14.0},
            ]
        },
        14.0,
    )

    assert [row["section_type"] for row in out] == ["chorus", "bridge", "instrumental_break"]
    assert out[0]["source_label"] == "Hook 1"
    assert all(0.6 <= row["normalization_confidence"] <= 1.0 for row in out)



def test_sections_merge_micro_sections_into_compatible_neighbors():
    out = normalized_sections(
        {
            "sections": [
                {"name": "Verse 1", "start_sec": 0.0, "end_sec": 8.0},
                {"name": "Break", "start_sec": 8.0, "end_sec": 9.5},
                {"name": "Chorus", "start_sec": 9.5, "end_sec": 16.0},
            ]
        },
        16.0,
    )

    assert [row["section_type"] for row in out] == ["verse", "chorus"]
    assert out[0]["end_sec"] == 9.5



def test_sections_merged_type_prefers_more_prominent_boundary():
    assert merged_shot_section_type({"section_type": "verse"}, {"section_type": "pre_chorus"}) == "pre_chorus"
    assert merged_shot_section_type({"section_type": "pre_chorus"}, {"section_type": "chorus"}) == "chorus"
    assert merged_shot_section_type({"section_type": "bridge"}, {"section_type": "post_chorus"}) == "bridge"
