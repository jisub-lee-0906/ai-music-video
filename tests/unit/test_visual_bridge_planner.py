import ai_mv.engines.visual_bridge.planner as bridge_planner

from ai_mv.engines.visual_bridge.planner import build_visual_brief


def test_visual_bridge_builds_strict_brief(monkeypatch):
    monkeypatch.setattr(bridge_planner, "generate_structured", _fake_generate)
    payload = {
        "audio_map": {
            "profile_intent": {
                "audio_intent": {"brief": "bright city-pop groove with glossy synths", "hook_brief": "night hook", "tags": [], "language": "ja"},
                "world_intent": {"visual_brief": "neon nightlife", "story_world": "one city night", "action_vocabulary": "small graceful actions", "payoff_style": "clear return"},
                "negative_intent": {"visual_negative": "no drift", "mv_avoid": "no clutter"},
            },
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
    assert out["recurring_location_families"]
    assert out["allowed_visual_variation"]


def test_visual_bridge_prompt_separates_names_and_timing():
    audio_map = {
        "profile_intent": {
            "audio_intent": {"brief": "glossy retro pop", "hook_brief": "night drive", "tags": [], "language": "ja"},
            "world_intent": {"visual_brief": "neon harbor nightlife with graceful poise", "story_world": "retro japanese city-pop lane", "action_vocabulary": "small actions", "payoff_style": "clear hero payoff"},
            "negative_intent": {"visual_negative": "no drift", "mv_avoid": "no clutter"},
        },
        "section_semantics": [
            {"section_name": "intro", "section_label": "intro", "movement_bias": "travel coverage", "release_level": "low"},
            {"section_name": "chorus", "section_label": "chorus", "movement_bias": "clear hero payoff", "release_level": "high"},
        ],
    }
    sections = [
        {"name": "intro", "start_sec": 0.0, "end_sec": 6.0},
        {"name": "chorus", "start_sec": 6.0, "end_sec": 14.0},
    ]
    prompt = bridge_planner._planner_prompt({}, audio_map, sections)
    assert "Section names only=intro, chorus" in prompt
    assert "Section labels in order=intro, chorus" in prompt
    assert "section_name must be a bare section token only" in prompt
    assert "single source of truth for the visual pipeline" in prompt
    assert "recurring_location_families" in prompt
    assert "allowed_visual_variation" in prompt
    assert "story_beat must be a visible present-tense action" in prompt
    assert "motion_axis" in prompt
    assert "Location grammar=budget=2-3 recurring families; examples=reflective threshold, lit passage, open night lane, sheltered edge" in prompt
    assert "Audio intent=glossy retro pop" in prompt
    assert "World intent=neon harbor nightlife with graceful poise" in prompt
    assert "Section semantics=intro|travel coverage|low, chorus|clear hero payoff|high" in prompt
    assert "Chorus 2 and Final Chorus must escalate without becoming a new world" in prompt


def test_visual_bridge_rejects_non_action_story_beat():
    bad = {
        "hero_identity": "hero",
        "world_rules": "world",
        "recurring_location_families": ["reflective threshold"],
        "allowed_visual_variation": ["framing changes"],
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
                "location_anchor": "reflective threshold",
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
        "recurring_location_families": ["reflective threshold", "open night lane"],
        "allowed_visual_variation": ["framing changes", "palette accents"],
        "visual_motifs": ["neon reflections", "chrome microphone"],
        "negative_constraints": ["identity drift", "period change"],
        "section_briefs": [
            {
                "section_name": "verse",
                "emotional_arc": "cool anticipation",
                "palette_hint": "teal and blue",
                "lighting_hint": "soft rim light",
                "staging_hint": "clean stage depth",
                "story_beat": "passes through the threshold without looking back",
                "location_anchor": "reflective threshold",
                "escalation_level": "steady",
                "motion_axis": "travel line",
            },
            {
                "section_name": "chorus",
                "emotional_arc": "bright release",
                "palette_hint": "pink and gold",
                "lighting_hint": "wide spotlight bloom",
                "staging_hint": "expanded performance space",
                "story_beat": "opens up in the same lane with clearer confidence",
                "location_anchor": "reflective threshold",
                "escalation_level": "payoff",
                "motion_axis": "gaze shift",
            },
        ],
    }
