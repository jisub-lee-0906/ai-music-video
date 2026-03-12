import pytest

from ai_mv.core.profile_brief import build_profile_brief, resolve_style_guidance, validate_profile_brief_config


def _profile() -> dict:
    return {
        "audio": {
            "language": "ja",
            "brief": "Explicit audio brief.",
            "hook_brief": "Explicit hook brief.",
        },
        "visual": {
            "brief": "Explicit visual brief.",
            "negative": "Explicit visual negative.",
        },
        "mv": {
            "story_world": "Explicit story world.",
            "action_vocabulary": "Explicit actions.",
            "payoff_style": "Explicit payoff style.",
            "avoid": "Explicit avoid.",
        },
    }


def test_validate_profile_brief_config_requires_explicit_fields():
    bad = {"audio": {"brief": "only audio"}}
    with pytest.raises(ValueError):
        validate_profile_brief_config(bad)


def test_build_profile_brief_uses_only_explicit_fields():
    brief = build_profile_brief(_profile())
    assert "Explicit audio brief" in brief["audio_direction"]
    assert "Explicit hook brief" in brief["hook_direction"]
    assert "Explicit visual brief" in brief["visual_direction"]
    assert "Explicit visual negative" in brief["negative_direction"]


def test_resolve_style_guidance_uses_brief_fields_only():
    text = resolve_style_guidance(_profile())
    assert "Explicit audio brief." in text
    assert "Explicit visual brief." in text
    assert "Explicit story world." in text
    assert "Explicit actions." in text
    assert "Explicit payoff style." in text
