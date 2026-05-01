from ai_mv.core.planning.render_item_payload import build_render_item_payload



def test_render_item_payload_module_builds_core_fields_and_ia2v_audio_segment():
    shot = {
        "shot_id": "S001",
        "section_id": "SEC_001",
        "material_id": "MAT_001",
        "start_sec": 3.0,
        "duration_sec": 5.0,
    }
    render_planning = {"render_priority_score": 0.9, "lane_priority_score": 0.85}
    reference_policy = {
        "reference_mode": "use_anchor_still",
        "reference_source_shot_id": "S000",
        "identity_lock_strength": "strong",
    }
    variation_delta = {
        "edit_variation_scope": "performance_pose_upgrade",
        "minimum_visual_delta": "pose_or_camera_change_required",
    }

    out = build_render_item_payload(
        shot=shot,
        render_mode="ia2v",
        render_count=2,
        render_planning=render_planning,
        render_seed=1234,
        variation_seed=2345,
        variation_profile={"variation_family": "editorial-a"},
        continuity_contract={"protagonist_anchor": "same lead"},
        shot_relation_contract={"relation_to_previous_shot": "sequence opener"},
        prompt_bundle={
            "prompt_seed": "seed text",
            "prompt_draft": "draft text",
            "prompt_polish": "polish text",
        },
        still_prompt_text="still prompt",
        clip_prompt_seed="clip seed",
        clip_positive_prompt="clip positive",
        edit_intent={"pattern_family": "hook_punch_in"},
        reference_policy=reference_policy,
        variation_delta=variation_delta,
    )

    assert out["shot_id"] == "S001"
    assert out["render_priority_score"] == 0.9
    assert out["prompt_polish"] == "polish text"
    assert out["reference_source_shot_id"] == "S000"
    assert out["minimum_visual_delta"] == "pose_or_camera_change_required"
    assert out["audio_segment"] == {"start_sec": 3.0, "duration_sec": 5.0}
    assert out["still_a"] == ""



def test_render_item_payload_module_skips_audio_segment_for_non_ia2v_modes():
    out = build_render_item_payload(
        shot={"shot_id": "S002", "start_sec": 8.0, "duration_sec": 4.0},
        render_mode="image",
        render_count=1,
        render_planning={"render_priority_score": 0.64},
        render_seed=1111,
        variation_seed=2222,
        variation_profile={"variation_family": "editorial-b"},
        continuity_contract={},
        shot_relation_contract={},
        prompt_bundle={
            "prompt_seed": "seed text",
            "prompt_draft": "draft text",
            "prompt_polish": "polish text",
        },
        still_prompt_text="still prompt",
        clip_prompt_seed="clip seed",
        clip_positive_prompt="clip positive",
        edit_intent={},
        reference_policy={
            "reference_mode": "",
            "reference_source_shot_id": "",
            "identity_lock_strength": "",
        },
        variation_delta={
            "edit_variation_scope": "",
            "minimum_visual_delta": "",
        },
    )

    assert "audio_segment" not in out
