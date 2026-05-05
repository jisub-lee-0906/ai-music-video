from ai_mv.core.planning.pose_anchor_selection import build_pose_anchor_selection
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


def test_greenhouse_source_bound_need_selects_tending_pose_anchor():
    selection = build_pose_anchor_selection(
        _shot(
            shot_role="protagonist tends seedlings in a greenhouse row",
            story_contract={"protagonist_action": "tends small seedlings with careful hands"},
            concept_text="k-indie greenhouse music video, one solitary protagonist in a green apron tends small seedlings, no city, no books",
        )
    )

    assert selection["selected_pose_anchor_id"] == "ANCHOR_POSE_GREENHOUSE_TENDING"
    assert selection["required_pose_family"] == "greenhouse_tending"
    assert selection["required_body_action"] == "source_bound_seedling_tending"
    assert selection["decision_method"] == "source_bound_pose_action_need"
    assert selection["source_bound_terms"] == ["greenhouse", "seedlings", "plants"]
    joined = " ".join(str(value) for value in selection.values()).lower()
    assert "city" not in joined
    assert "books" not in joined


def test_lighthouse_source_bound_need_selects_cliff_wind_pose_anchor():
    selection = build_pose_anchor_selection(
        _shot(
            shot_role="protagonist stands by a weathered lighthouse above ocean cliffs",
            visual_mode="world_bridge",
            story_function="release",
            concept_text="j-rock lighthouse music video, one solitary protagonist in a red windbreaker stands by a weathered lighthouse above ocean cliffs, no desert, no radio",
        )
    )

    assert selection["selected_pose_anchor_id"] == "ANCHOR_POSE_LIGHTHOUSE_CLIFF_STANCE"
    assert selection["required_pose_family"] == "lighthouse_cliff_stance"
    assert selection["required_body_action"] == "source_bound_cliff_wind_stance"
    assert selection["source_bound_terms"] == ["lighthouse", "cliff", "wind"]
    joined = " ".join(str(value) for value in selection.values()).lower()
    assert "desert" not in joined
    assert "radio" not in joined


def test_arctic_source_bound_need_selects_ice_crossing_pose_anchor_without_neon_rooftop_leak():
    selection = build_pose_anchor_selection(
        _shot(
            shot_role="protagonist crosses an ice field under aurora",
            story_contract={"protagonist_action": "crosses an ice field with empty hands"},
            concept_text="synth arctic music video, one solitary protagonist crosses an ice field under aurora, no city, no neon, no rooftop, no stage, no crowd",
        )
    )

    assert selection["selected_pose_anchor_id"] == "ANCHOR_POSE_ARCTIC_ICE_CROSSING"
    assert selection["required_pose_family"] == "arctic_ice_crossing"
    assert selection["required_motion_direction"] == "diagonal_forward"
    assert selection["source_bound_terms"] == ["arctic", "ice", "aurora"]
    joined = " ".join(str(value) for value in selection.values()).lower()
    assert "neon" not in joined
    assert "rooftop" not in joined
    assert "stage" not in joined
    assert "crowd" not in joined


def test_negative_only_world_terms_do_not_select_specific_world_pose_anchor():
    selection = build_pose_anchor_selection(
        _shot(
            story_contract={"protagonist_action": "walks forward with empty hands"},
            concept_text="quiet indoor music video, one solitary protagonist waits by a window, no greenhouse, no lighthouse, no arctic, no aurora",
        )
    )

    assert selection["selected_pose_anchor_id"] not in {
        "ANCHOR_POSE_GREENHOUSE_TENDING",
        "ANCHOR_POSE_LIGHTHOUSE_CLIFF_STANCE",
        "ANCHOR_POSE_ARCTIC_ICE_CROSSING",
    }


def test_render_item_selected_pose_anchor_follows_source_bound_pose_action_need():
    item = build_render_item(
        {},
        "k-indie greenhouse music video, one solitary protagonist in a green apron tends small seedlings under warm glasshouse light, no city",
        "citypop",
        get_style_bible("citypop"),
        _shot(
            shot_id="S_GREEN",
            shot_role="protagonist tends seedlings in greenhouse rows",
            story_contract={"protagonist_action": "tends small seedlings with careful hands"},
        ),
    )

    assert item["selected_pose_anchor_id"] == "ANCHOR_POSE_GREENHOUSE_TENDING"
    assert item["pose_action_need"]["selected_pose_anchor_id"] == "ANCHOR_POSE_GREENHOUSE_TENDING"
    assert item["pose_action_need"]["pose_family"] == "greenhouse_tending"
