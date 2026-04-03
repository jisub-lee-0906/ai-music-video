import pytest

from ai_mv.core.director_brief import build_director_brief_intent, validate_director_brief_config


def _brief() -> dict:
    return {
        "brief": "director_brief_example",
        "audio": {"language": "ko", "brief": "Audio brief", "hook_brief": "Hook brief"},
        "visual": {
            "story_premise": "A heroine moves through one connected station-side night world.",
            "world_rules": "The world stays physically connected and readable.",
            "heroine_arc": "She grows clearer in direction as she keeps moving.",
            "forbidden_story_moves": "Avoid dream resets and sudden extra characters.",
            "section_story_roles": {"Intro": "She crosses the first boundary into the world."},
        },
        "character": {
            "identity_core": "The same Korean female idol",
            "identity_hooks": ["with a high ponytail"],
            "anchor_wardrobe_guidance": "Polished off-duty idol styling.",
            "anchor_avoid": "Avoid stage costume styling.",
        },
    }


def test_validate_director_brief_requires_story_only_fields():
    with pytest.raises(ValueError):
        validate_director_brief_config({"audio": {"brief": "x"}})


def test_build_director_brief_intent_returns_writer_layer_fields():
    intent = build_director_brief_intent(_brief())
    assert intent["identity_core"] == "The same Korean female idol"
    assert intent["story_premise"]
    assert intent["world_rules"]
    assert intent["heroine_arc"]
    assert "Intro" in intent["section_story_roles"]
    assert intent["motif_families"] == []
