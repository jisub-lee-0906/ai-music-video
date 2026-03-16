import pytest

from ai_mv.core.profile_brief import build_profile_intent, validate_profile_brief_config


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
            "outro_feel": "Explicit outro feel.",
            "avoid": "Explicit avoid.",
        },
    }


def test_validate_profile_brief_config_requires_explicit_fields():
    bad = {"audio": {"brief": "only audio"}}
    with pytest.raises(ValueError):
        validate_profile_brief_config(bad)


def test_build_profile_intent_uses_only_explicit_fields():
    intent = build_profile_intent(_profile())
    assert intent["audio_intent"]["brief"] == "Explicit audio brief."
    assert intent["audio_intent"]["hook_brief"] == "Explicit hook brief."
    assert intent["world_intent"]["visual_intent"] == "Explicit visual brief."
    assert intent["negative_intent"]["visual_negative"] == "Explicit visual negative."
    assert intent["negative_intent"]["mv_avoid"] == "Explicit avoid."
    assert intent["escalation_intent"]["outro_residue"] == "Explicit outro feel."
