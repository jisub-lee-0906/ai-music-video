import ai_mv.engines.visual_story_bible.planner as bridge_planner

from ai_mv.engines.visual_story_bible.planner import build_visual_story_bible


def test_visual_story_bible_builds_strict_contract(monkeypatch):
    monkeypatch.setattr(bridge_planner, "generate_structured", _fake_generate)
    payload = {
        "profile_intent": {
        "world_intent": {"visual_intent": "neon nightlife", "story_world": "one city night", "action_vocabulary": "small graceful actions", "payoff_style": "clear return"},
            "negative_intent": {"visual_negative": "no drift", "mv_avoid": "no clutter"},
        },
        "lyrics_timeline": _timeline(),
    }
    out = build_visual_story_bible({}, payload)
    assert out["hero_identity_lock"]
    assert len(out["lyric_beats"]) == 2
    assert out["lyric_beats"][1]["section_name"] == "chorus"
    assert out["lyric_beats"][0]["visible_action"]
    assert out["lyric_beats"][0]["location_family"]
    assert out["recurring_location_families"]
    assert out["heroine_invariants"]
    assert out["world_invariants"]
    assert out["closeup_rules"]
    assert out["repeat_escalation_rules"]


def test_visual_story_bible_prompt_mentions_lyric_first_contract():
    payload = {
        "profile_intent": {
        "world_intent": {"visual_intent": "neon harbor nightlife with graceful poise", "story_world": "retro japanese city-pop lane", "action_vocabulary": "small actions", "payoff_style": "clear hero payoff"},
            "negative_intent": {"visual_negative": "no drift", "mv_avoid": "no clutter"},
        },
        "lyrics_timeline": _timeline(),
    }
    prompt = bridge_planner._planner_prompt({}, payload)
    assert "Write a lyric-first visual story bible for downstream image and video workflows" in prompt
    assert "Required top-level fields: hero_identity_lock, world_rules, recurring_location_families, forbidden_drift, lyric_beats, section_progression, repeat_escalation_rules" in prompt
    assert "Create exactly one lyric_beats item for each lyric_timeline beat in the same order" in prompt
    assert "Do not split, merge, invent, omit, or rewrite beat ids" in prompt
    assert "Lyric beat manifest=" in prompt
    assert "Lyric timeline=" in prompt
    assert "World support=neon harbor nightlife with graceful poise" in prompt
    assert "Forbidden drift=no drift" in prompt


def _fake_generate(_config, _prompt, _schema, **_kwargs):
    return {
        "hero_identity_lock": "silver-haired city-pop heroine with polished stage styling",
        "world_rules": "retro neon nightlife world with elegant concert geometry",
        "recurring_location_families": ["reflective threshold", "open night lane"],
        "forbidden_drift": ["identity drift", "period change"],
        "lyric_beats": [
            {
                "beat_id": "LB01_01",
                "section_name": "intro",
                "section_label": "Intro",
                "line_refs": [1],
                "literal_image": "rainy glass threshold",
                "visible_action": "she slows at the threshold and watches her reflection",
                "emotional_turn": "cool anticipation",
                "continuity_anchor": "reflective threshold return",
                "payoff_role": "entry",
                "repeat_variant_of": "",
                "location_family": "reflective threshold",
                "palette_hint": "teal and blue",
                "lighting_hint": "soft rim light",
                "camera_commitment": "a medium shot with clean stage depth",
                "composition_shape": "an off-center silhouette near dark glass",
                "space_event": "The threshold light flickers across the glass",
                "palette_mode": "bubblegum pink and aqua cyan with deep navy",
                "character_render_mode": "sharp almond eyes with thick hair shapes",
            },
            {
                "beat_id": "LB02_01",
                "section_name": "chorus",
                "section_label": "Chorus",
                "line_refs": [1, 2],
                "literal_image": "open lane with silver reflections",
                "visible_action": "she opens into the lane and holds the look forward",
                "emotional_turn": "bright release",
                "continuity_anchor": "open lane payoff return",
                "payoff_role": "release",
                "repeat_variant_of": "",
                "location_family": "open night lane",
                "palette_hint": "pink and gold",
                "lighting_hint": "wide spotlight bloom",
                "camera_commitment": "a wide shot in expanded performance space",
                "composition_shape": "a small figure against stacked flat bands",
                "space_event": "The open lane widens and the sign light pulses",
                "palette_mode": "coral pink and lavender purple with blue-black",
                "character_render_mode": "a long-limbed fashion figure",
            },
        ],
        "section_progression": [
            {"section_name": "intro", "section_label": "Intro", "dominant_emotion": "anticipation", "story_function": "entry", "lyric_beat_ids": ["LB01_01"]},
            {"section_name": "chorus", "section_label": "Chorus", "dominant_emotion": "release", "story_function": "payoff", "lyric_beat_ids": ["LB02_01"]},
        ],
        "repeat_escalation_rules": ["repeat hooks must change action or camera commitment"],
    }


def _timeline() -> dict:
    return {
        "sections": [
            {
                "section_name": "intro",
                "section_label": "Intro",
                "lines": [{"line_index": 1, "text": "rain on glass"}],
                "hook_lines": [],
                "lyric_beats": [
                    {
                        "beat_id": "LB01_01",
                        "line_refs": [1],
                        "literal_image": "rainy glass threshold",
                        "visible_action": "she slows at the threshold and watches her reflection",
                        "emotional_turn": "cool anticipation",
                        "continuity_anchor": "reflective threshold return",
                        "payoff_role": "entry",
                        "repeat_variant_of": "",
                    }
                ],
            },
            {
                "section_name": "chorus",
                "section_label": "Chorus",
                "lines": [{"line_index": 1, "text": "open lane"}, {"line_index": 2, "text": "hold the look"}],
                "hook_lines": [1],
                "lyric_beats": [
                    {
                        "beat_id": "LB02_01",
                        "line_refs": [1, 2],
                        "literal_image": "open lane with silver reflections",
                        "visible_action": "she opens into the lane and holds the look forward",
                        "emotional_turn": "bright release",
                        "continuity_anchor": "open lane payoff return",
                        "payoff_role": "release",
                        "repeat_variant_of": "",
                    }
                ],
            },
        ]
    }
