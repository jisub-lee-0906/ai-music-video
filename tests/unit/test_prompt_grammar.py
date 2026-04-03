from ai_mv.core.prompt_grammar import (
    golden_shot_guidance,
    load_ref_archetype_grammars,
    load_tti_grammars,
    load_wan_grammars,
    ref_archetype_grammar,
    ref_archetype_variant,
)
from ai_mv.core.stages.tti_anchor import build_tti_anchor_master_prompt


def _config() -> dict:
    return {
        "brief": "director_brief_example",
        "audio": {"brief": "Audio brief", "hook_brief": "Hook brief"},
        "visual": {"brief": "Visual brief", "negative": "Visual negative"},
        "mv": {
            "story_world": "Night city transit world",
            "payoff_style": "Cinematic release",
            "outro_feel": "Lingering after-image",
            "avoid": "Avoid list",
        },
        "character": {
            "identity_core": "same heroine",
            "identity_hooks": ["high ponytail"],
            "anchor_wardrobe_guidance": "polished off-duty idol styling",
            "anchor_avoid": "avoid costume styling",
        },
        "director": {
            "target_style": "cinematic live-action music video",
            "world_core": "night city",
        },
    }


def test_prompt_grammar_files_load_expected_families():
    ref = load_ref_archetype_grammars()
    tti = load_tti_grammars()
    wan = load_wan_grammars()
    assert "window_contact" in ref["archetypes"]
    assert ref_archetype_variant("window_contact", "moving_vehicle_window")["note"]
    assert len(tti["anchor_families"]) >= 3
    assert len(wan["transition_families"]) >= 4


def test_ref_archetype_contract_data_is_structured():
    grammar = ref_archetype_grammar("threshold_crossing")
    assert grammar["contract"]
    assert grammar["good_pattern"]
    assert grammar["preferred_sentence_shape"]
    assert "threshold" in " ".join(grammar["surface_priority"]).lower()


def test_golden_shot_guidance_loads_priority_probe_shapes():
    guidance = golden_shot_guidance("bridge_b1")
    assert guidance["preferred_surface"] == "wet platform edge"
    assert "footprints" in guidance["preferred_pattern"].lower()
    assert "yellow tactile line" in guidance["preferred_pattern"].lower()


def test_platform_edge_grammar_uses_directional_foot_change_shape():
    grammar = ref_archetype_grammar("platform_edge")
    lowered = grammar["preferred_sentence_shape"].lower()
    assert "crossing" in lowered or "shorter" in lowered or "next step" in lowered
    assert "tactile" in " ".join(grammar["surface_priority"]).lower() or "yellow line" in " ".join(grammar["surface_priority"]).lower()


def test_tti_master_prompt_uses_grammar_memory():
    prompt = build_tti_anchor_master_prompt(_config())
    lowered = prompt.lower()
    assert "full-body" in lowered
    assert "neutral backdrop" in lowered or "pale grey" in lowered
    assert "footwear" in lowered
