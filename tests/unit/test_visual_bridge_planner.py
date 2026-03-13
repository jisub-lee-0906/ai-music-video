import ai_mv.engines.visual_bridge.planner as bridge_planner

from ai_mv.engines.visual_bridge.planner import build_visual_brief


def test_visual_bridge_builds_strict_brief(monkeypatch):
    monkeypatch.setattr(bridge_planner, "generate_structured", _fake_generate)
    payload = {
        "audio_map": {
            "tags": "city pop, female vocal",
            "style_guidance": "neon nightlife",
            "genre_description": "bright city-pop groove with glossy synths",
            "lyrics": "[Verse - Pulse]\nshining through the night",
            "sections": [
                {"name": "verse", "start_sec": 0.0, "end_sec": 10.0},
                {"name": "chorus", "start_sec": 10.0, "end_sec": 20.0},
            ],
        }
    }
    out = build_visual_brief({}, payload)
    assert out["hero_identity"]
    assert len(out["section_briefs"]) == 2
    assert out["section_briefs"][1]["section_name"] == "chorus"
    assert out["section_briefs"][0]["story_beat"]
    assert out["section_briefs"][0]["location_anchor"]


def test_visual_bridge_prompt_separates_names_and_timing():
    audio_map = {
        "tags": "city pop",
        "style_guidance": "night drive",
        "genre_description": "glossy retro pop",
        "profile_summary": "retro japanese city-pop lane",
        "visual_direction": "neon harbor nightlife with graceful poise",
        "negative_direction": "no futuristic sci-fi tone",
        "lyrics": "line one\nline two",
    }
    sections = [
        {"name": "intro", "start_sec": 0.0, "end_sec": 6.0},
        {"name": "chorus", "start_sec": 6.0, "end_sec": 14.0},
    ]
    prompt = bridge_planner._planner_prompt(audio_map, sections)
    assert "Section names only=intro, chorus" in prompt
    assert "Section labels in order=intro, chorus" in prompt
    assert "Timing reference=intro(0.0-6.0), chorus(6.0-14.0)" in prompt
    assert "section_name must be a bare section token only" in prompt
    assert "Chorus 2 should feel like a stronger return" in prompt
    assert "Create a small location budget for the whole song" in prompt
    assert "story_beat must be a short plain-English visible action beat" in prompt
    assert "Every story_beat must contain at least one visible action verb" in prompt
    assert "Good story_beat examples: slows by the glass and checks the reflection" in prompt
    assert "Bad story_beat examples: searching, opening up, separation" in prompt
    assert "Style lane=night drive" in prompt
    assert "Audio direction=glossy retro pop" in prompt
    assert "Visual direction=neon harbor nightlife with graceful poise" in prompt
    assert "Derive identity strictly from the profile and visual brief" in prompt
    assert "never infer ethnicity, gender, genre-specific styling" in prompt
    assert "Audio tags=" not in prompt


def test_visual_bridge_rejects_non_action_story_beat():
    bad = {
        "hero_identity": "hero",
        "world_rules": "world",
        "visual_motifs": ["rain"],
        "negative_constraints": ["drift"],
        "section_briefs": [
            {
                "section_name": "intro",
                "emotional_arc": "quiet",
                "palette_hint": "blue",
                "lighting_hint": "soft",
                "staging_hint": "still frame",
                "story_beat": "searching",
                "location_anchor": "station corridor glass",
            }
        ],
    }
    try:
        bridge_planner.normalize_visual_brief(bad, [{"name": "intro"}])
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert "story_beat must describe a visible action" in str(exc)


def _fake_generate(_config, _prompt, _schema):
    return {
        "hero_identity": "silver-haired city-pop heroine with polished stage styling",
        "world_rules": "retro neon nightlife world with elegant concert geometry",
        "visual_motifs": ["neon reflections", "chrome microphone"],
        "negative_constraints": ["identity drift", "period change"],
        "section_briefs": [
            {
                "section_name": "verse",
                "emotional_arc": "cool anticipation",
                "palette_hint": "teal and blue",
                "lighting_hint": "soft rim light",
                "staging_hint": "clean stage depth",
                "story_beat": "passes through the storefront without looking back",
                "location_anchor": "storefront pavement",
            },
            {
                "section_name": "chorus",
                "emotional_arc": "bright release",
                "palette_hint": "pink and gold",
                "lighting_hint": "wide spotlight bloom",
                "staging_hint": "expanded performance space",
                "story_beat": "opens up in the same street with clearer confidence",
                "location_anchor": "storefront pavement",
            },
        ],
    }
