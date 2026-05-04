from ai_mv.core.planning.continuity_contracts import (
    build_continuity_contract,
    build_shot_relation_contract,
)


def test_continuity_contract_module_preserves_explicit_wardrobe_anchor():
    shot = {
        "protagonist_anchor": "same lone night-walk protagonist, stable dark outerwear silhouette, no competing bystanders",
        "world_anchor": "same rain-slick neon boulevard world, wet asphalt reflections, dense urban signage",
        "continuity_contract": {
            "wardrobe_anchor": "stable bright stage outfit silhouette",
        },
    }

    out = build_continuity_contract(shot)

    assert out == {
        "protagonist_anchor": "same lone night-walk protagonist, stable dark outerwear silhouette, no competing bystanders",
        "world_anchor": "same rain-slick neon boulevard world, wet asphalt reflections, dense urban signage",
        "wardrobe_anchor": "stable bright stage outfit silhouette",
        "no_competing_subjects": True,
        "time_band_anchor": "same concept time and lighting band",
    }


def test_continuity_contract_defaults_do_not_force_night_time_band():
    out = build_continuity_contract(
        {
            "protagonist_anchor": "same forest protagonist",
            "world_anchor": "same forest pier world, moss and water",
        }
    )

    assert out["time_band_anchor"] == "same concept time and lighting band"
    assert "night" not in out["time_band_anchor"].lower()


def test_shot_relation_contract_module_builds_intro_and_followup_defaults():
    intro = build_shot_relation_contract({"section_type": "intro", "framing_intent": "establishing_wide"})
    followup = build_shot_relation_contract({"section_type": "chorus", "framing_intent": "hero_medium"})

    assert intro == {
        "relation_to_previous_shot": "sequence opener",
        "camera_distance_progression": "set baseline distance",
        "same_block_vs_new_block": "same block baseline",
        "emotional_delta": "establish opening emotional baseline",
    }
    assert followup == {
        "relation_to_previous_shot": "continue same protagonist and world from previous shot",
        "camera_distance_progression": "move closer than previous shot",
        "same_block_vs_new_block": "same block, new angle",
        "emotional_delta": "open into hook release without changing world",
    }
