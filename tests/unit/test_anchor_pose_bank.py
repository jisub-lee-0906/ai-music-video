from ai_mv.core.contracts.stage_io import StageInput
from ai_mv.core.planning.anchor_package import build_anchor_package
from ai_mv.core.planning.render_items import build_render_item
from ai_mv.styles.resolver import get_style_bible
from ai_mv.core.stages.render_stills import run_render_stills


def test_anchor_package_builds_white_background_pose_bank_from_single_tti_identity_anchor():
    package = build_anchor_package(
        concept_text="late-night city pop walk under wet neon lights, missed train, unresolved goodbye turning into quiet resolve",
        style_name="citypop",
        creative_direction={"protagonist_anchor": "one beautiful young Korean woman"},
    )

    anchors = package["anchors"]
    tti_anchors = [anchor for anchor in anchors if anchor["workflow_target"] == "image_flux2_text_to_image"]
    assert [anchor["anchor_id"] for anchor in tti_anchors] == ["ANCHOR_CHARACTER_UPPER_BODY"]

    pose_bank = package["pose_anchor_bank"]
    pose_ids = [anchor["anchor_id"] for anchor in pose_bank]
    assert len(pose_ids) >= 5
    assert len(set(pose_ids)) == len(pose_ids)
    assert "ANCHOR_POSE_HERO_CLOSEUP" in pose_ids
    assert "ANCHOR_POSE_THREE_QUARTER_MEDIUM" in pose_ids
    assert "ANCHOR_POSE_FULL_BODY_STANDING" in pose_ids
    assert "ANCHOR_POSE_WALKING_SIDE" in pose_ids
    assert "ANCHOR_POSE_PROFILE_EMOTIONAL" in pose_ids
    assert "ANCHOR_POSE_MICROPHONE_PERFORMANCE" in pose_ids
    microphone_anchor = next(anchor for anchor in pose_bank if anchor["anchor_id"] == "ANCHOR_POSE_MICROPHONE_PERFORMANCE")
    assert microphone_anchor["pose_family"] == "microphone_performance"
    assert "performance" in microphone_anchor["intended_shot_functions"]
    assert "microphone" in microphone_anchor["prompt_text"].lower()
    assert "no microphone" not in microphone_anchor["prompt_text"].lower()

    for anchor in pose_bank:
        assert anchor["anchor_role"] == "pose_variant"
        assert anchor["workflow_target"] == "image_flux2_reference_image"
        assert anchor["reference_anchor_ids"] == ["ANCHOR_CHARACTER_UPPER_BODY"]
        assert anchor["background_contract"] == "white_background"
        assert "same face identity" in anchor["identity_contract"]
        assert "same outfit" in anchor["identity_contract"]
        assert "pure white seamless background" in anchor["prompt_text"]
        assert "No street" in anchor["prompt_text"]
        assert anchor["pose_family"]
        assert anchor["framing"]
        assert anchor["camera_angle"]
        assert anchor["intended_shot_functions"]


def test_render_item_selects_distinct_pose_anchors_from_story_and_shot_needs():
    style_bible = get_style_bible("citypop")
    concept = "late-night city pop walk under wet neon lights"
    base = {
        "render_mode": "ia2v",
        "start_sec": 0.0,
        "duration_sec": 3.0,
        "section_id": "SEC_001",
        "section_type": "verse_1",
    }
    hero = build_render_item(
        {},
        concept,
        "citypop",
        style_bible,
        {
            **base,
            "shot_id": "S001",
            "shot_role": "hero emotional closeup",
            "visual_mode": "hero_closeup",
            "story_function": "threshold",
        },
    )
    walking = build_render_item(
        {},
        concept,
        "citypop",
        style_bible,
        {
            **base,
            "shot_id": "S002",
            "shot_role": "walking through wet neon street",
            "visual_mode": "walking_side_profile",
            "story_function": "search",
        },
    )
    payoff = build_render_item(
        {},
        concept,
        "citypop",
        style_bible,
        {
            **base,
            "shot_id": "S003",
            "shot_role": "final resolve payoff",
            "visual_mode": "final_payoff_front",
            "story_function": "payoff",
        },
    )
    microphone = build_render_item(
        {},
        concept,
        "citypop",
        style_bible,
        {
            **base,
            "shot_id": "S004",
            "shot_role": "chorus microphone performance",
            "visual_mode": "microphone_performance_medium",
            "story_function": "performance",
            "story_contract": {"protagonist_action": "singing into a handheld microphone"},
        },
    )

    assert hero["selected_pose_anchor_id"] == "ANCHOR_POSE_HERO_CLOSEUP"
    assert hero["pose_anchor_selection"]["required_framing"] in {"close", "medium_close"}
    assert walking["selected_pose_anchor_id"] == "ANCHOR_POSE_WALKING_SIDE"
    assert walking["pose_anchor_selection"]["required_camera_angle"] == "side"
    assert payoff["selected_pose_anchor_id"] == "ANCHOR_POSE_FINAL_PAYOFF_FRONT"
    assert microphone["selected_pose_anchor_id"] == "ANCHOR_POSE_MICROPHONE_PERFORMANCE"
    assert microphone["pose_anchor_selection"]["required_pose_family"] == "microphone_performance"
    assert len({hero["selected_pose_anchor_id"], walking["selected_pose_anchor_id"], payoff["selected_pose_anchor_id"], microphone["selected_pose_anchor_id"]}) == 4


def test_pose_anchor_selection_does_not_treat_unresolved_text_as_final_payoff():
    style_bible = get_style_bible("citypop")
    item = build_render_item(
        {},
        "unresolved goodbye under wet neon lights",
        "citypop",
        style_bible,
        {
            "shot_id": "S004",
            "render_mode": "ia2v",
            "start_sec": 3.0,
            "duration_sec": 3.0,
            "section_id": "SEC_002",
            "section_type": "verse_1",
            "shot_role": "searching walk after unresolved goodbye",
            "visual_mode": "walking_side_profile",
            "story_function": "search",
        },
    )

    assert item["selected_pose_anchor_id"] == "ANCHOR_POSE_WALKING_SIDE"



def test_render_stills_routes_keyframes_through_selected_pose_anchor(monkeypatch):
    calls = []

    def _fake_run_flux2_still(_config, item):
        calls.append(dict(item))
        return f"D:/renders/{item['shot_id']}.png"

    monkeypatch.setattr("ai_mv.core.stages.render_stills.run_flux2_still", _fake_run_flux2_still)
    stage_input = StageInput(
        run_id="run-pose-anchor-routing",
        config={"render": {"flux2_size": "1280x720"}},
        payload={
            "anchor_package": {
                "anchors": [
                    {
                        "anchor_id": "ANCHOR_CHARACTER_UPPER_BODY",
                        "anchor_type": "character_upper_body_identity",
                        "material_class": "character_reference_anchor",
                        "workflow_target": "image_flux2_text_to_image",
                        "prompt_text": "upper-body identity card, pure white seamless background, clear face visibility",
                    }
                ],
                "pose_anchor_bank": [
                    {
                        "anchor_id": "ANCHOR_POSE_HERO_CLOSEUP",
                        "anchor_type": "pose_variant",
                        "anchor_role": "pose_variant",
                        "material_class": "pose_reference_anchor",
                        "workflow_target": "image_flux2_reference_image",
                        "reference_anchor_ids": ["ANCHOR_CHARACTER_UPPER_BODY"],
                        "pose_family": "hero_closeup",
                        "framing": "close",
                        "camera_angle": "front",
                        "prompt_text": "hero close-up, same face identity, same outfit, pure white seamless background, No street",
                    },
                    {
                        "anchor_id": "ANCHOR_POSE_WALKING_SIDE",
                        "anchor_type": "pose_variant",
                        "anchor_role": "pose_variant",
                        "material_class": "pose_reference_anchor",
                        "workflow_target": "image_flux2_reference_image",
                        "reference_anchor_ids": ["ANCHOR_CHARACTER_UPPER_BODY"],
                        "pose_family": "walking",
                        "framing": "full",
                        "camera_angle": "side",
                        "prompt_text": "walking side pose, same face identity, same outfit, pure white seamless background, No street",
                    },
                ],
            },
            "shot_plan": [
                {"shot_id": "S001", "visual_mode": "hero_closeup"},
                {"shot_id": "S002", "visual_mode": "walking_side_profile"},
            ],
            "render_plan": [
                {
                    "shot_id": "S001",
                    "still_prompt_text": "same lead woman in close emotional neon keyframe",
                    "selected_pose_anchor_id": "ANCHOR_POSE_HERO_CLOSEUP",
                    "continuity_contract": {"protagonist_anchor": "same lead woman", "world_anchor": "same wet neon"},
                },
                {
                    "shot_id": "S002",
                    "still_prompt_text": "same lead woman walking through wet neon",
                    "selected_pose_anchor_id": "ANCHOR_POSE_WALKING_SIDE",
                    "continuity_contract": {"protagonist_anchor": "same lead woman", "world_anchor": "same wet neon"},
                },
            ],
        },
    )

    out = run_render_stills(stage_input)

    assert [call["shot_id"] for call in calls] == [
        "ANCHOR_CHARACTER_UPPER_BODY",
        "ANCHOR_POSE_HERO_CLOSEUP",
        "ANCHOR_POSE_WALKING_SIDE",
        "S001",
        "S002",
    ]
    assert calls[1]["reference_image"] == "D:/renders/ANCHOR_CHARACTER_UPPER_BODY.png"
    assert calls[2]["reference_image"] == "D:/renders/ANCHOR_CHARACTER_UPPER_BODY.png"
    assert calls[3]["reference_image"] == "D:/renders/ANCHOR_POSE_HERO_CLOSEUP.png"
    assert calls[4]["reference_image"] == "D:/renders/ANCHOR_POSE_WALKING_SIDE.png"
    assert out.payload["still_results"][0]["selected_pose_anchor_id"] == "ANCHOR_POSE_HERO_CLOSEUP"
    assert out.payload["still_results"][1]["selected_pose_anchor_id"] == "ANCHOR_POSE_WALKING_SIDE"
    assert out.payload["workflow_inputs"]["stills"]["pose_anchor_count"] == 2



def test_pose_anchor_rendering_requires_upper_body_identity_reference(monkeypatch):
    calls = []

    def _fake_run_flux2_still(_config, item):
        calls.append(dict(item))
        return f"D:/renders/{item['shot_id']}.png"

    monkeypatch.setattr("ai_mv.core.stages.render_stills.run_flux2_still", _fake_run_flux2_still)
    stage_input = StageInput(
        run_id="run-pose-anchor-strict-upper-ref",
        config={"render": {"flux2_size": "1280x720"}},
        payload={
            "anchor_package": {
                "anchors": [
                    {
                        "anchor_id": "ANCHOR_WORLD_CHARACTER",
                        "anchor_type": "world_character_anchor",
                        "material_class": "world_reference_anchor",
                        "workflow_target": "image_flux2_text_to_image",
                        "prompt_text": "rainy neon city world with one red-coated woman",
                    }
                ],
                "pose_anchor_bank": [
                    {
                        "anchor_id": "ANCHOR_POSE_HERO_CLOSEUP",
                        "anchor_type": "pose_variant",
                        "anchor_role": "pose_variant",
                        "material_class": "pose_reference_anchor",
                        "workflow_target": "image_flux2_reference_image",
                        "reference_anchor_ids": ["ANCHOR_CHARACTER_UPPER_BODY"],
                        "prompt_text": "hero close-up, same face identity, pure white seamless background",
                    }
                ],
            },
            "shot_plan": [],
            "render_plan": [],
        },
    )

    out = run_render_stills(stage_input)

    assert [call["shot_id"] for call in calls] == ["ANCHOR_WORLD_CHARACTER"]
    assert [row["anchor_id"] for row in out.payload["anchor_results"]] == ["ANCHOR_WORLD_CHARACTER"]
    assert out.payload["workflow_inputs"]["stills"]["pose_anchor_count"] == 0



def test_keyframe_reference_fallback_uses_primary_identity_not_world_anchor(monkeypatch):
    calls = []

    def _fake_run_flux2_still(_config, item):
        calls.append(dict(item))
        return f"D:/renders/{item['shot_id']}.png"

    monkeypatch.setattr("ai_mv.core.stages.render_stills.run_flux2_still", _fake_run_flux2_still)
    stage_input = StageInput(
        run_id="run-primary-identity-fallback",
        config={"render": {"flux2_size": "1280x720"}},
        payload={
            "anchor_package": {
                "anchors": [
                    {
                        "anchor_id": "ANCHOR_WORLD_CHARACTER",
                        "anchor_type": "world_character_anchor",
                        "material_class": "world_reference_anchor",
                        "workflow_target": "image_flux2_text_to_image",
                        "prompt_text": "rainy neon city world with one red-coated woman",
                    },
                    {
                        "anchor_id": "ANCHOR_CHARACTER_UPPER_BODY",
                        "anchor_type": "character_upper_body_identity",
                        "material_class": "character_reference_anchor",
                        "workflow_target": "image_flux2_text_to_image",
                        "prompt_text": "upper-body identity card, pure white seamless background, clear face visibility",
                    },
                ],
                "pose_anchor_bank": [],
            },
            "shot_plan": [{"shot_id": "S001", "visual_mode": "hero_closeup"}],
            "render_plan": [
                {
                    "shot_id": "S001",
                    "still_prompt_text": "same lead woman in close emotional neon keyframe",
                    "continuity_contract": {"protagonist_anchor": "same lead woman", "world_anchor": "same wet neon"},
                }
            ],
        },
    )

    run_render_stills(stage_input)

    assert [call["shot_id"] for call in calls] == ["ANCHOR_WORLD_CHARACTER", "ANCHOR_CHARACTER_UPPER_BODY", "S001"]
    assert calls[-1]["reference_image"] == "D:/renders/ANCHOR_CHARACTER_UPPER_BODY.png"



def test_keyframe_with_missing_selected_pose_anchor_does_not_fall_back_to_world_anchor(monkeypatch):
    calls = []

    def _fake_run_flux2_still(_config, item):
        calls.append(dict(item))
        return f"D:/renders/{item['shot_id']}.png"

    monkeypatch.setattr("ai_mv.core.stages.render_stills.run_flux2_still", _fake_run_flux2_still)
    stage_input = StageInput(
        run_id="run-missing-pose-no-world-fallback",
        config={"render": {"flux2_size": "1280x720"}},
        payload={
            "anchor_package": {
                "anchors": [
                    {
                        "anchor_id": "ANCHOR_WORLD_CHARACTER",
                        "anchor_type": "world_character_anchor",
                        "material_class": "world_reference_anchor",
                        "workflow_target": "image_flux2_text_to_image",
                        "prompt_text": "rainy neon city world with one red-coated woman",
                    }
                ],
                "pose_anchor_bank": [],
            },
            "shot_plan": [{"shot_id": "S001", "visual_mode": "hero_closeup"}],
            "render_plan": [
                {
                    "shot_id": "S001",
                    "still_prompt_text": "same lead woman in close emotional neon keyframe",
                    "selected_pose_anchor_id": "ANCHOR_POSE_HERO_CLOSEUP",
                    "continuity_contract": {"protagonist_anchor": "same lead woman", "world_anchor": "same wet neon"},
                }
            ],
        },
    )

    run_render_stills(stage_input)

    assert [call["shot_id"] for call in calls] == ["ANCHOR_WORLD_CHARACTER", "S001"]
    assert "reference_image" not in calls[-1]
