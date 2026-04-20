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



def test_sections_apply_appendix_alias_table_for_direct_canonical_mappings():
    out = normalized_sections(
        {
            "sections": [
                {"name": "Cold Open", "start_sec": 0.0, "end_sec": 3.0},
                {"name": "V1", "start_sec": 3.0, "end_sec": 7.0},
                {"name": "Post", "start_sec": 7.0, "end_sec": 10.0},
                {"name": "End", "start_sec": 10.0, "end_sec": 14.0},
            ]
        },
        14.0,
    )

    assert [row["section_type"] for row in out] == ["intro", "verse", "post_chorus", "outro"]
    assert all(row["normalization_confidence"] >= 0.8 for row in out)



def test_sections_merge_low_confidence_section_when_neighbors_match_energy_band():
    out = normalized_sections(
        {
            "sections": [
                {"name": "Verse 1", "start_sec": 0.0, "end_sec": 8.0},
                {"name": "Liftlet", "start_sec": 8.0, "end_sec": 10.8},
                {"name": "Chorus", "start_sec": 10.8, "end_sec": 16.0},
            ]
        },
        16.0,
    )

    assert [row["section_type"] for row in out] == ["verse", "chorus"]
    assert out[0]["source_label"] == "Verse 1"
    assert out[0]["end_sec"] == 10.8



def test_sections_keep_long_unknown_section_boundaries_even_when_confidence_is_weak():
    out = normalized_sections(
        {
            "sections": [
                {"name": "Verse 1", "start_sec": 0.0, "end_sec": 8.0},
                {"name": "Mystery", "start_sec": 8.0, "end_sec": 16.0},
                {"name": "Chorus", "start_sec": 16.0, "end_sec": 24.0},
            ]
        },
        24.0,
    )

    assert [row["section_type"] for row in out] == ["verse", "verse", "chorus"]
    assert out[1]["source_label"] == "Mystery"
    assert out[1]["duration_sec"] == 8.0



def test_sections_merge_high_confidence_post_chorus_micro_sections():
    out = normalized_sections(
        {
            "sections": [
                {"name": "Verse 1", "start_sec": 0.0, "end_sec": 8.0},
                {"name": "Post", "start_sec": 8.0, "end_sec": 9.0},
                {"name": "Chorus", "start_sec": 9.0, "end_sec": 16.0},
            ]
        },
        16.0,
    )

    assert [row["section_type"] for row in out] == ["verse", "chorus"]
    assert out[0]["end_sec"] == 9.0



def test_sections_merged_type_prefers_more_prominent_boundary():
    assert merged_shot_section_type({"section_type": "verse"}, {"section_type": "pre_chorus"}) == "pre_chorus"
    assert merged_shot_section_type({"section_type": "pre_chorus"}, {"section_type": "chorus"}) == "chorus"
    assert merged_shot_section_type({"section_type": "bridge"}, {"section_type": "post_chorus"}) == "bridge"
