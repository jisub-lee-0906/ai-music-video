from ai_mv.core.profile_brief import build_profile_brief


def test_profile_brief_builds_reusable_direction_fields():
    out = build_profile_brief(
        [
            "japanese city pop",
            "female solo vocal",
            "glossy electric piano",
            "warm analog synth pad",
            "subtle disco bounce",
        ],
        "retro japanese city-pop mood, elegant adult romance, no futuristic sci-fi tone",
    )
    assert "japanese city pop" in out["profile_summary"].lower()
    assert "female solo vocal" in out["audio_direction"].lower()
    assert "bounce" in out["audio_direction"].lower()
    assert "retro japanese city-pop mood" in out["visual_direction"].lower()
    assert "city pop" not in out["hook_direction"].lower()
    assert "no futuristic sci-fi tone" in out["negative_direction"].lower()
