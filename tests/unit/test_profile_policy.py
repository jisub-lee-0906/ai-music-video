from ai_mv.core.profile_policy import resolve_profile_policy


def test_resolve_profile_policy_derives_defaults_from_profile_text():
    cfg = {
        "visual": {
            "brief": "A photorealistic cinematic city-pop video with a young adult East Asian heroine, selective extreme close-ups, reflective thresholds, and controlled center framing before extra motion.",
        },
        "mv": {
            "story_world": "The same night, the same heroine, and recurring environment families: reflective thresholds, lit passages, and open lanes.",
            "payoff_style": "One extreme close-up seals the return.",
        },
    }
    out = resolve_profile_policy(cfg)
    assert out["visual_mode"] == "character_heavy" or out["visual_mode"] == "balanced"
    assert out["continuity_mode"] == "same_heroine"
    assert out["face_policy"] == "payoff_only"
    assert "Final Chorus" in out["direct_face_sections"]
    assert out["ref_policy"] in {"identity_sensitive_only", "endpoints"}


def test_resolve_profile_policy_honors_explicit_visual_policy():
    cfg = {
        "visual": {"brief": "environment-led video"},
        "mv": {"story_world": "same heroine and same world", "payoff_style": "controlled payoff"},
        "visual_policy": {
            "visual_mode": "environment_first",
            "face_policy": "avoid",
            "ref_policy": "minimal",
            "direct_face_sections": ["Bridge"],
        },
    }
    out = resolve_profile_policy(cfg)
    assert out["visual_mode"] == "environment_first"
    assert out["face_policy"] == "avoid"
    assert out["ref_policy"] == "minimal"
    assert out["direct_face_sections"] == ["Bridge"]
