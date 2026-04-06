from ai_mv.core.prompt_grammar import load_flux2_prompting, load_render_verbalizer_rules
from ai_mv.core.stages.tti_anchor import build_tti_anchor_master_prompt


def _config() -> dict:
    return {
        "brief": "director_brief_example",
        "audio": {"brief": "Audio brief", "hook_brief": "Hook brief"},
        "visual": {
            "story_premise": "A grounded cinematic night-world follows one singer through connected places.",
            "world_rules": "Keep places readable and physically connected.",
            "heroine_arc": "She becomes more direct over time.",
            "forbidden_story_moves": "Avoid sudden resets or extra characters.",
        },
        "character": {
            "identity_core": "same heroine",
            "identity_hooks": ["high ponytail"],
            "anchor_wardrobe_guidance": "polished off-duty idol styling",
            "anchor_avoid": "avoid costume styling",
        },
    }


def test_active_prompt_grammar_files_load():
    flux = load_flux2_prompting()
    verbalizer = load_render_verbalizer_rules()
    assert flux["ref"]["natural_language_contract"]
    assert flux["tti"]["hierarchy"]
    assert flux["wan"]["suppression"]
    assert verbalizer["ref_instruction_lines"]
    assert verbalizer["wan_instruction_lines"]


def test_tti_master_prompt_stays_clean_and_direct():
    prompt = build_tti_anchor_master_prompt(_config())
    lowered = prompt.lower()
    assert "reusable identity anchor" in lowered
    assert "soft controlled lighting" in lowered
    assert "clear face readability" in lowered
    assert "identity priority" not in lowered
    assert "subject first" not in lowered
