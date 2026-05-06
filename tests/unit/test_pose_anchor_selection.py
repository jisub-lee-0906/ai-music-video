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


def test_lighthouse_search_need_selects_cliff_wind_pose_anchor():
    selection = build_pose_anchor_selection(
        _shot(
            shot_role="protagonist stands by a weathered lighthouse above ocean cliffs",
            visual_mode="world_bridge",
            story_function="search",
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


def test_lighthouse_source_bound_need_uses_story_function_sub_anchors():
    concept = "j-rock lighthouse music video, one solitary protagonist in a red windbreaker stands by a weathered lighthouse above ocean cliffs, no desert, no radio"

    wound = build_pose_anchor_selection(
        _shot(
            shot_role="protagonist pauses at the lighthouse threshold above ocean cliffs",
            visual_mode="live_house_entry",
            story_function="wound_setup",
            concept_text=concept,
        )
    )
    release = build_pose_anchor_selection(
        _shot(
            shot_role="protagonist faces fierce wind by the lighthouse beacon above ocean cliffs",
            visual_mode="chorus_charge",
            story_function="release",
            concept_text=concept,
        )
    )

    assert wound["selected_pose_anchor_id"] == "ANCHOR_POSE_LIGHTHOUSE_LOOKOUT_STANCE"
    assert wound["required_pose_family"] == "lighthouse_lookout_stance"
    assert release["selected_pose_anchor_id"] == "ANCHOR_POSE_LIGHTHOUSE_WIND_FACE"
    assert release["required_pose_family"] == "lighthouse_wind_face"


def test_arctic_search_need_selects_ice_crossing_pose_anchor_without_neon_rooftop_leak():
    selection = build_pose_anchor_selection(
        _shot(
            shot_role="protagonist crosses an ice field under aurora",
            story_function="search",
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


def test_arctic_source_bound_need_uses_story_function_sub_anchors():
    concept = "synth arctic music video, one solitary protagonist crosses an ice field under aurora, no city, no neon, no rooftop, no stage, no crowd"

    wound = build_pose_anchor_selection(
        _shot(
            shot_role="protagonist looks up under a faint aurora over the ice field",
            visual_mode="laser_horizon",
            story_function="wound_setup",
            concept_text=concept,
        )
    )
    release = build_pose_anchor_selection(
        _shot(
            shot_role="protagonist holds still in cold blue light after crossing the ice field",
            visual_mode="grid_surge",
            story_function="release",
            concept_text=concept,
        )
    )

    assert wound["selected_pose_anchor_id"] == "ANCHOR_POSE_ARCTIC_AURORA_LOOKUP"
    assert wound["required_pose_family"] == "arctic_aurora_lookup"
    assert release["selected_pose_anchor_id"] == "ANCHOR_POSE_ARCTIC_COLD_FIELD_PAUSE"
    assert release["required_pose_family"] == "arctic_cold_field_pause"


def test_lighthouse_pose_anchor_requires_world_action_not_generic_face_or_wardrobe_only_source():
    selection = build_pose_anchor_selection(
        _shot(
            shot_role="hero face closeup with direct gaze",
            visual_mode="hero_face_performance",
            story_function="release",
            concept_text="indie music video, one solitary protagonist wears a red windbreaker, no lighthouse, no cliff, no ocean",
        )
    )

    assert selection["selected_pose_anchor_id"] not in {
        "ANCHOR_POSE_LIGHTHOUSE_CLIFF_STANCE",
        "ANCHOR_POSE_LIGHTHOUSE_LOOKOUT_STANCE",
        "ANCHOR_POSE_LIGHTHOUSE_WIND_FACE",
    }


def test_lighthouse_wind_face_requires_release_world_action_not_search_face_closeup():
    selection = build_pose_anchor_selection(
        _shot(
            shot_role="hero face closeup near the lighthouse",
            visual_mode="hero_face_performance",
            story_function="search",
            concept_text="j-rock lighthouse music video, one solitary protagonist in a red windbreaker stands by a weathered lighthouse above ocean cliffs",
        )
    )

    assert selection["selected_pose_anchor_id"] != "ANCHOR_POSE_LIGHTHOUSE_WIND_FACE"


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
        "ANCHOR_POSE_LIGHTHOUSE_LOOKOUT_STANCE",
        "ANCHOR_POSE_LIGHTHOUSE_WIND_FACE",
        "ANCHOR_POSE_ARCTIC_ICE_CROSSING",
        "ANCHOR_POSE_ARCTIC_AURORA_LOOKUP",
        "ANCHOR_POSE_ARCTIC_COLD_FIELD_PAUSE",
    }


def test_inline_negative_world_terms_do_not_select_specific_world_pose_anchor():
    selection = build_pose_anchor_selection(
        _shot(
            shot_role="protagonist crosses wind-carved snow toward a warm signal beacon",
            story_contract={"protagonist_action": "crosses wind-carved snow with empty hands"},
            story_function="search",
            concept_text=(
                "synthwave arctic research station music video, one explorer in a silver parka "
                "crosses wind-carved snow with no ocean and no lighthouse"
            ),
        )
    )

    assert selection["selected_pose_anchor_id"] not in {
        "ANCHOR_POSE_LIGHTHOUSE_CLIFF_STANCE",
        "ANCHOR_POSE_LIGHTHOUSE_LOOKOUT_STANCE",
        "ANCHOR_POSE_LIGHTHOUSE_WIND_FACE",
    }
    assert "lighthouse" not in selection.get("source_bound_terms", [])
    assert "ocean" not in selection.get("source_bound_terms", [])


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
