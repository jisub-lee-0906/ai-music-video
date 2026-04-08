import pytest

from ai_mv.core.director_brief import build_director_brief_intent, validate_director_brief_config


def _brief() -> dict:
    return {
        "brief": "director_brief_example",
        "prompt": "A lonely night walk after a breakup that grows more direct in the chorus.",
        "genre": "synth pop",
        "voice": "solo female, airy and emotional",
        "language": "ko",
        "visual_concept": "Realistic cinematic city-night breakup video.",
        "locations": ["dim retro diner", "wet city street at night"],
        "props": ["worn notebook", "coffee mug"],
    }


def test_validate_director_brief_requires_story_only_fields():
    with pytest.raises(ValueError):
        validate_director_brief_config({"prompt": "x", "genre": "y"})


def test_build_director_brief_intent_returns_writer_layer_fields():
    intent = build_director_brief_intent(_brief())
    assert intent["identity_core"] == "same anchor character"
    assert intent["story_premise"]
    assert intent["audio_brief"]
    assert intent["performer_arc"]
    assert intent["anchor_subject"] == "young adult woman"
    assert intent["anchor_pose"]
    assert intent["anchor_background"]
    assert intent["visual_concept"] == "Realistic cinematic city-night breakup video."
    assert intent["profile_locations"] == ["dim retro diner", "wet city street at night"]
    assert intent["profile_props"] == ["worn notebook", "coffee mug"]
    assert "Intro" in intent["section_story_roles"]
    assert intent["motif_families"] == []
