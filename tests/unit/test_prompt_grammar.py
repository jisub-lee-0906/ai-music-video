from ai_mv.core.prompt_grammar import (
    golden_structure_guidance,
    load_flux2_prompting,
    load_ref_archetype_grammars,
    load_tti_families,
    load_wan_transitions,
    ref_archetype_grammar,
    ref_archetype_variant,
)
from ai_mv.core.stages.tti_anchor import build_tti_anchor_master_prompt


def _config() -> dict:
    return {
        "brief": "director_brief_example",
        "audio": {"brief": "Audio brief", "hook_brief": "Hook brief"},
        "visual": {
            "story_premise": "A heroine moves through a connected night world.",
            "world_rules": "The world must stay physically connected and readable.",
            "heroine_arc": "She gains clearer direction with each section.",
            "forbidden_story_moves": "Avoid sudden dream resets or extra characters.",
        },
        "character": {
            "identity_core": "same heroine",
            "identity_hooks": ["high ponytail"],
            "anchor_wardrobe_guidance": "polished off-duty idol styling",
            "anchor_avoid": "avoid costume styling",
        },
    }


def test_prompt_grammar_files_load_expected_families():
    ref = load_ref_archetype_grammars()
    tti = load_tti_families()
    wan = load_wan_transitions()
    flux = load_flux2_prompting()
    assert "window_contact" in ref["archetypes"]
    assert ref_archetype_variant("window_contact", "moving_vehicle_window")["note"]
    assert len(tti["families"]) >= 3
    assert len(wan["families"]) >= 4
    assert flux["ref"]["natural_language_contract"]
    assert flux["tti"]["hierarchy"]
    assert flux["wan"]["suppression"]
    assert "single-reference" in flux["runtime_note"].lower()


def test_ref_archetype_contract_data_is_structured():
    grammar = ref_archetype_grammar("threshold_crossing")
    assert grammar["prompt_contract"]
    assert grammar["preferred_sentence_shape"]
    assert grammar["story_uses"]
    assert "threshold" in " ".join(grammar["surface_priority"]).lower()


def test_golden_structure_guidance_loads_priority_shapes():
    guidance = golden_structure_guidance("pressure", "platform_edge", "bridge_motion")
    assert guidance["preferred_surface"] == "wet platform edge"
    assert "yellow tactile line" in guidance["preferred_pattern"].lower()
    assert "footprint" in guidance["preferred_pattern"].lower()


def test_golden_structure_guidance_loads_threshold_handoff_variant():
    guidance = golden_structure_guidance("handoff", "threshold_crossing", "passage_exit")
    assert guidance["preferred_surface"] == "station threshold"
    assert "wet passage" in guidance["preferred_pattern"].lower()


def test_platform_edge_grammar_uses_directional_foot_change_shape():
    grammar = ref_archetype_grammar("platform_edge")
    lowered = grammar["preferred_sentence_shape"].lower()
    assert "crossing" in lowered or "shorter" in lowered or "next step" in lowered
    assert "tactile" in " ".join(grammar["surface_priority"]).lower() or "yellow line" in " ".join(grammar["surface_priority"]).lower()


def test_tti_master_prompt_uses_grammar_memory():
    prompt = build_tti_anchor_master_prompt(_config())
    lowered = prompt.lower()
    assert "reusable identity anchor" in lowered
    assert "soft controlled lighting" in lowered
    assert "clear face readability" in lowered
    assert "identity priority" not in lowered
    assert "subject first" not in lowered
