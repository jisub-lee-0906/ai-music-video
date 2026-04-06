from ai_mv.core.contracts.prompt_normalize import normalize_flux2_ref_items, normalize_lyrics_timeline


def test_normalize_flux2_ref_preserves_long_optional_clauses():
    anchors = [{"shot_id": "S001"}]
    raw_items = [
        {
            "shot_id": "S001",
            "prompt_text": "The same anime girl, now hero turns and smiles. Neon city skyline. Flat cel shading, thick clean outlines.",
            "subject_clause": " ".join([f"word{i}" for i in range(1, 30)]),
            "action_clause": "hero turns and smiles",
            "camera_clause": "neon city skyline",
            "continuity_clause": "keeps same lane",
        },
    ]

    out = normalize_flux2_ref_items(raw_items, anchors)
    clause = out["S001"]["subject_clause"]
    assert clause == " ".join(f"word{i}" for i in range(1, 30))


def test_normalize_lyrics_timeline_allows_empty_intro_and_outro_sections():
    sections = [
        {"name": "intro", "label": "Intro", "start_sec": 0.0, "end_sec": 8.0},
        {"name": "verse_1", "label": "Verse 1", "start_sec": 8.0, "end_sec": 28.0},
        {"name": "outro", "label": "Outro", "start_sec": 28.0, "end_sec": 36.0},
    ]
    raw = {
        "sections": [
            {"section_name": "intro", "section_label": "Intro", "lines": [], "hook_lines": [], "lyric_beats": []},
            {
                "section_name": "verse_1",
                "section_label": "Verse 1",
                "lines": [{"line_index": 1, "text": "개찰구 불빛 아래 숨을 고르고"}],
                "hook_lines": [],
                "lyric_beats": [
                    {
                        "beat_id": "verse_1_b1",
                        "line_refs": [1],
                        "literal_image": "ticket gate light",
                        "visible_action": "she slows under the gate light",
                        "emotional_turn": "distance becomes active",
                        "continuity_anchor": "wet station threshold",
                        "payoff_role": "setup",
                        "repeat_variant_of": "",
                    }
                ],
            },
            {"section_name": "outro", "section_label": "Outro", "lines": [], "hook_lines": [], "lyric_beats": []},
        ]
    }
    out = normalize_lyrics_timeline(raw, sections)
    assert out["sections"][0]["lines"] == []
    assert out["sections"][0]["lyric_beats"] == []
    assert out["sections"][2]["lines"] == []
    assert out["sections"][2]["lyric_beats"] == []
