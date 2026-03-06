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
            },
            {
                "section_name": "chorus",
                "emotional_arc": "bright release",
                "palette_hint": "pink and gold",
                "lighting_hint": "wide spotlight bloom",
                "staging_hint": "expanded performance space",
            },
        ],
    }
