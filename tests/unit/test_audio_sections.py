import pytest

import ai_mv.engines.acestep_1_5_split.runner as audio_runner


def test_sections_preserve_verse_ids():
    blocks = [
        {"section": "intro", "lines": ["a"]},
        {"section": "verse_1", "lines": ["b"]},
        {"section": "verse_2", "lines": ["c"]},
        {"section": "outro", "lines": ["d"]},
    ]
    out = audio_runner._sections(100.0, blocks)
    names = [x["name"] for x in out]
    assert "verse_1" in names
    assert "verse_2" in names


def test_sections_reject_outro_not_last():
    blocks = [
        {"section": "intro", "lines": ["a"]},
        {"section": "outro", "lines": ["b"]},
        {"section": "chorus", "lines": ["c"]},
    ]
    with pytest.raises(RuntimeError):
        audio_runner._sections(100.0, blocks)


def test_sections_reject_invalid_transition():
    blocks = [
        {"section": "intro", "lines": ["a"]},
        {"section": "chorus", "lines": ["b"]},
        {"section": "verse_1", "lines": ["c"]},
        {"section": "outro", "lines": ["d"]},
    ]
    with pytest.raises(RuntimeError):
        audio_runner._sections(100.0, blocks)


def test_sections_allow_same_section_repeat():
    blocks = [
        {"section": "intro", "lines": ["a"]},
        {"section": "verse_1", "lines": ["b"]},
        {"section": "verse_1", "lines": ["c"]},
        {"section": "outro", "lines": ["d"]},
    ]
    out = audio_runner._sections(100.0, blocks)
    names = [x["name"] for x in out]
    assert names.count("verse_1") == 2
