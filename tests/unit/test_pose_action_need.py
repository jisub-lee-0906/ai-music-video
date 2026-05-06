from ai_mv.core.planning.pose_action_need import build_pose_action_need
from ai_mv.core.planning.render_items import build_render_item
from ai_mv.styles.resolver import get_style_bible


def _shot(**overrides):
    base = {
        "shot_id": "S001",
        "render_mode": "ia2v",
        "start_sec": 0.0,
        "duration_sec": 3.0,
        "section_id": "SEC_001",
        "section_type": "verse_1",
        "shot_role": "quiet story beat",
        "visual_mode": "medium_story",
        "story_function": "search",
        "story_contract": {},
    }
    base.update(overrides)
    return base


def test_final_payoff_pose_action_need_is_low_risk_front_readable():
    need = build_pose_action_need(
        _shot(
            section_type="outro",
            visual_mode="final_payoff_front",
            story_function="payoff",
            shot_role="resolved final face-to-camera payoff",
        ),
        "k-indie greenhouse music video, one solitary protagonist in a green apron tends small seedlings",
    )

    assert need["pose_family"] == "final_payoff_front"
    assert need["risk_tier"] == "low"
    assert need["camera_angle"] == "front"
    assert need["face_readability"] == "high"
    assert need["wardrobe_readability"] == "upper_body_required"
    assert "same_identity" in need["qa_requirements"]


def test_source_bound_greenhouse_need_allows_seedling_interaction_without_forbidden_inventions():
    need = build_pose_action_need(
        _shot(
            shot_role="protagonist tends seedlings in a warm glasshouse row",
            story_function="search",
            story_contract={"protagonist_action": "tends small seedlings with careful hands"},
        ),
        "k-indie greenhouse music video, one solitary protagonist in a green apron tends small seedlings under warm glasshouse light, no city, no rain, no books",
    )

    assert need["world_interaction"] == "tending source-bound seedlings or plants"
    assert need["allowed_props"] == []
    assert need["source_bound_terms"] == ["greenhouse", "seedlings", "plants"]
    joined = " ".join(str(value) for value in need.values()).lower()
    assert "books" not in joined
    assert "city" not in joined
    assert "rain" not in joined


def test_lighthouse_need_uses_source_bound_wind_cliff_stance_without_desert_radio_invention():
    need = build_pose_action_need(
        _shot(
            shot_role="protagonist stands by a weathered lighthouse above ocean cliffs",
            visual_mode="world_bridge",
            story_function="release",
        ),
        "j-rock lighthouse music video, one solitary protagonist in a red windbreaker stands by a weathered lighthouse above ocean cliffs, fierce resolve after loss, no desert, no radio",
    )

    assert need["world_interaction"] == "standing in source-bound lighthouse cliff wind"
    assert need["pose_family"] == "lighthouse_cliff_stance"
    joined = " ".join(str(value) for value in need.values()).lower()
    assert "lighthouse" in joined
    assert "cliff" in joined
    assert "desert" not in joined
    assert "radio" not in joined


def test_windbreaker_wardrobe_alone_does_not_create_lighthouse_world_need():
    need = build_pose_action_need(
        _shot(
            shot_role="hero face closeup with direct gaze",
            visual_mode="hero_face_performance",
            story_function="release",
        ),
        "indie music video, one solitary protagonist wears a red windbreaker, no lighthouse, no cliff, no ocean",
    )

    joined = " ".join(str(value) for value in need.values()).lower()
    assert "lighthouse" not in joined
    assert "cliff" not in joined
    assert need["source_bound_terms"] == []


def test_arctic_research_station_does_not_turn_research_into_ocean_lighthouse_need():
    need = build_pose_action_need(
        _shot(
            shot_role="protagonist crosses wind-carved snow toward a warm signal beacon",
            visual_mode="laser_horizon",
            story_function="search",
            story_contract={"protagonist_action": "crosses wind-carved snow with empty hands"},
        ),
        (
            "synthwave arctic research station music video, one explorer in a silver parka "
            "crosses wind-carved snow toward a warm signal beacon with no ocean and no lighthouse, "
            "no city, no rooftop, no satellite, no dark outerwear"
        ),
    )

    assert need["world_interaction"] == "moving through source-bound arctic ice field"
    assert need["source_bound_terms"] == ["arctic", "snow"]
    joined = " ".join(str(value) for value in need.values()).lower()
    assert "lighthouse" not in joined
    assert "cliff" not in joined
    assert "ocean" not in joined
    assert "wind" not in need["source_bound_terms"]


def test_negative_only_world_terms_do_not_become_positive_pose_need_sources():
    need = build_pose_action_need(
        _shot(story_contract={"protagonist_action": "walks forward with empty hands, no microphone"}),
        "synthwave arctic music video, one solitary protagonist crosses an ice field, no city, no neon, no rooftop, no stage, no crowd",
    )

    joined = " ".join(str(value) for value in need.values()).lower()
    assert "arctic" in joined or "ice" in joined
    assert "city" not in joined
    assert "neon" not in joined
    assert "rooftop" not in joined
    assert "stage" not in joined
    assert "microphone" not in joined


def test_render_item_surfaces_pose_action_need_next_to_selected_pose_anchor():
    item = build_render_item(
        {},
        "k-indie greenhouse music video, one solitary protagonist in a green apron tends small seedlings under warm glasshouse light",
        "citypop",
        get_style_bible("citypop"),
        _shot(
            shot_id="S_GREEN",
            shot_role="protagonist tends seedlings in greenhouse rows",
            story_contract={"protagonist_action": "tends small seedlings with careful hands"},
        ),
    )

    assert item["pose_action_need"]["world_interaction"] == "tending source-bound seedlings or plants"
    assert item["pose_action_need"]["selected_pose_anchor_id"] == item["selected_pose_anchor_id"]
    assert item["pose_action_need"]["qa_requirements"] == [
        "same_identity",
        "same_wardrobe",
        "single_protagonist",
        "source_bound_world",
    ]
