from ai_mv.core.planning.production_policy import build_production_policy
from ai_mv.core.planning.render_items import build_render_item
from ai_mv.styles.citypop.bible import get_citypop_bible


def test_production_policy_routes_hero_face_to_upper_anchor_with_green_risk():
    policy = build_production_policy(
        {
            "shot_role": "hero_face_performance",
            "visual_mode": "chorus_performance",
            "section_type": "chorus",
            "duration_sec": 5.0,
        },
        style_name="idol_pop",
    )

    assert policy["candidate_role"] == "hero_face_performance"
    assert policy["anchor_reference_arm"] == "B_UPPER_ONLY"
    assert policy["ia2v_risk_class"] == "green"
    assert policy["recommended_duration_sec"] == {"min": 0.8, "max": 1.8}
    assert "face_stability" in policy["review_focus"]


def test_production_policy_marks_hand_water_glow_as_high_risk_interaction():
    policy = build_production_policy(
        {
            "shot_role": "final_payoff",
            "story_function": "payoff",
            "visual_event": "one coherent hand reaches toward glowing water in a puddle",
            "payoff_requirement": "touch the moonlike glowing puddle reflection",
            "duration_sec": 5.0,
        },
        style_name="citypop",
    )

    assert policy["candidate_role"] == "high_risk_interaction_payoff"
    assert policy["anchor_reference_arm"] == "D_FULLBODY_UPPER"
    assert policy["ia2v_risk_class"] == "red"
    assert policy["recommended_duration_sec"]["max"] <= 0.8
    assert "hover_or_reaction_alternative_required" in policy["safety_rules"]
    assert "start_middle_end_review_required" in policy["safety_rules"]


def test_production_policy_routes_release_payoff_away_from_repeated_hero_face_role():
    chorus_release = build_production_policy(
        {
            "shot_role": "chorus_lift",
            "visual_mode": "chorus_performance",
            "section_type": "chorus",
            "story_function": "release",
            "visual_event": "symbolic neon reflection flares across the wet street as the chorus opens up",
            "framing_intent": "release_wide",
            "duration_sec": 4.0,
        },
        style_name="citypop",
    )
    final_payoff = build_production_policy(
        {
            "shot_role": "final_payoff",
            "visual_mode": "ending_resolution_still",
            "section_type": "outro",
            "story_function": "payoff",
            "visual_event": "the protagonist becomes a small figure in the neon skyline after the final lyric",
            "framing_intent": "release_wide",
            "duration_sec": 4.0,
        },
        style_name="citypop",
    )

    assert chorus_release["candidate_role"] == "symbolic_insert"
    assert chorus_release["anchor_reference_arm"] == "A_FULLBODY_ONLY"
    assert final_payoff["candidate_role"] == "world_bridge"
    assert final_payoff["anchor_reference_arm"] == "F_FULLBODY_UPPER_WORLD"



def test_production_policy_applies_genre_safety_profile():
    policy = build_production_policy(
        {
            "shot_role": "chorus_lift",
            "visual_mode": "group_choreography_stage",
            "section_type": "chorus",
            "genre_lane": "KPOP_STAGE",
            "duration_sec": 6.0,
        },
        style_name="idol_pop",
    )

    assert policy["genre_profile"]["genre_lane"] == "KPOP_STAGE"
    assert "solo_hero_performance" in policy["genre_profile"]["prefer"]
    assert "full_group_choreography_long_take" in policy["genre_profile"]["avoid"]
    assert policy["ia2v_risk_class"] in {"yellow", "red"}


def test_render_item_surfaces_production_policy_metadata():
    out = build_render_item(
        {},
        "late-night city pop walk under wet neon lights",
        "citypop",
        get_citypop_bible(),
        {
            "shot_id": "S009",
            "section_id": "SEC_004",
            "render_mode": "ia2v",
            "shot_role": "final_payoff",
            "section_type": "outro",
            "section_name": "Outro",
            "story_function": "payoff",
            "visual_event": "hand hovering above a glowing puddle reflection",
            "payoff_requirement": "the light reflects on the protagonist face instead of direct contact",
            "start_sec": 14.0,
            "duration_sec": 4.0,
        },
    )

    assert out["candidate_role"] == "high_risk_interaction_payoff"
    assert out["ia2v_risk_class"] == "red"
    assert out["anchor_reference_arm"] == "D_FULLBODY_UPPER"
    assert out["recommended_duration_sec"]["max"] <= 0.8
    assert "production_policy" in out
