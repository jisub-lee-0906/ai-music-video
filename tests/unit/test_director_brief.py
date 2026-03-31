import pytest

from ai_mv.core.director_brief import build_director_brief_intent, validate_director_brief_config


def _brief() -> dict:
    return {
        "audio": {"language": "ko", "brief": "Audio brief", "hook_brief": "Hook brief"},
        "visual": {"brief": "Visual brief", "negative": "Visual negative"},
        "mv": {
            "story_world": "Story world",
            "action_vocabulary": "Actions",
            "payoff_style": "Payoff style",
            "outro_feel": "Outro feel",
            "avoid": "Avoid list",
        },
        "character": {"identity_core": "same heroine", "identity_hooks": ["red ribbon"]},
        "director": {
            "target_style": "anime style",
            "world_core": "night world",
            "camera_bias": "readable anime framing",
            "lighting_bias": "sign glow",
            "shadow_bias": "cel shaded shadows",
            "motion_bias": "stable 2d anime motion",
            "transition_bias": "previous-end continuity",
            "motif_families": ["train window", "ticket gate"],
        },
    }


def test_validate_director_brief_requires_explicit_fields():
    with pytest.raises(ValueError):
        validate_director_brief_config({"audio": {"brief": "x"}})


def test_validate_director_brief_allows_optional_director_bias_fields():
    brief = _brief()
    brief["director"].pop("camera_bias", None)
    brief["director"].pop("lighting_bias", None)
    brief["director"].pop("motion_bias", None)
    validate_director_brief_config(brief)


def test_build_director_brief_intent_returns_identity_and_section_grammar():
    intent = build_director_brief_intent(_brief())
    assert intent["identity_core"] == "same heroine"
    assert intent["style_contract"] == "anime style"
    assert intent["motif_families"] == ["train window", "ticket gate"]
    assert "Intro" in intent["section_grammar"]
