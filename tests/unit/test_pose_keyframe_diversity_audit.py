from ai_mv.core.planning.pose_keyframe_diversity_audit import audit_pose_keyframe_diversity


def test_pose_keyframe_diversity_audit_counts_selected_and_materialized_pose_anchors():
    preview = {
        "workflow_prompt_lint": {"status": "pass"},
        "anchor_package": {
            "pose_anchor_bank": [
                {"anchor_id": "ANCHOR_CHARACTER_FULL_BODY"},
                {"anchor_id": "ANCHOR_POSE_HERO_CLOSEUP"},
                {"anchor_id": "ANCHOR_POSE_WALKING_SIDE"},
            ],
        },
        "render_plan": [
            {
                "shot_id": "S001",
                "section_id": "verse_1",
                "section_type": "verse",
                "story_function": "threshold",
                "visual_mode": "hero_closeup",
                "candidate_role": "hero_face_performance",
                "selected_pose_anchor_id": "ANCHOR_POSE_HERO_CLOSEUP",
                "workflow_prompts": {"flux2_ref_still": {"positive_text": "medium close-up with readable face"}},
            },
            {
                "shot_id": "S002",
                "section_id": "pre_chorus",
                "section_type": "pre_chorus",
                "story_function": "search",
                "visual_mode": "walking movement",
                "candidate_role": "world_bridge",
                "selected_pose_anchor_id": "ANCHOR_POSE_WALKING_SIDE",
                "workflow_prompts": {"ltx_ia2v": {"positive_text": "camera: locked medium-wide shot with a gentle lateral drift."}},
            },
            {
                "shot_id": "S003",
                "section_id": "chorus",
                "section_type": "chorus",
                "story_function": "performance",
                "visual_mode": "hero_closeup",
                "candidate_role": "hero_face_performance",
                "selected_pose_anchor_id": "ANCHOR_POSE_HERO_CLOSEUP",
            },
        ],
    }

    audit = audit_pose_keyframe_diversity(preview)

    assert audit["shot_count"] == 3
    assert audit["selected_pose_anchor_counts"] == {
        "ANCHOR_POSE_HERO_CLOSEUP": 2,
        "ANCHOR_POSE_WALKING_SIDE": 1,
    }
    assert audit["materialized_pose_anchor_ids"] == [
        "ANCHOR_CHARACTER_FULL_BODY",
        "ANCHOR_POSE_HERO_CLOSEUP",
        "ANCHOR_POSE_WALKING_SIDE",
    ]
    assert audit["missing_materialized_selected_pose_anchor_ids"] == []
    assert audit["risk_tier_counts"] == {"low": 2, "medium": 1}
    assert audit["rows"][1]["still_camera"] == ""
    assert audit["rows"][1]["clip_camera"] == "locked medium-wide shot with a gentle lateral drift"


def test_pose_keyframe_diversity_audit_flags_anchor_concentration_and_missing_materialization():
    preview = {
        "workflow_prompt_lint": {"status": "pass"},
        "anchor_package": {"pose_anchor_bank": [{"anchor_id": "ANCHOR_POSE_HERO_CLOSEUP"}]},
        "render_plan": [
            {"shot_id": "S001", "selected_pose_anchor_id": "ANCHOR_POSE_HERO_CLOSEUP"},
            {"shot_id": "S002", "selected_pose_anchor_id": "ANCHOR_POSE_HERO_CLOSEUP"},
            {"shot_id": "S003", "selected_pose_anchor_id": "ANCHOR_POSE_HERO_CLOSEUP"},
            {"shot_id": "S004", "selected_pose_anchor_id": "ANCHOR_POSE_MICROPHONE_PERFORMANCE"},
        ],
    }

    audit = audit_pose_keyframe_diversity(preview, concentration_warn_ratio=0.6)

    assert audit["missing_materialized_selected_pose_anchor_ids"] == ["ANCHOR_POSE_MICROPHONE_PERFORMANCE"]
    assert any(issue["code"] == "pose_anchor_concentration" for issue in audit["issues"])
    assert any(issue["code"] == "selected_pose_anchor_not_materialized" for issue in audit["issues"])
    assert audit["risk_tier_counts"] == {"low": 3, "high": 1}


def test_pose_keyframe_diversity_audit_counts_pose_action_need_world_interactions():
    preview = {
        "workflow_prompt_lint": {"status": "pass"},
        "anchor_package": {
            "pose_anchor_bank": [
                {"anchor_id": "ANCHOR_POSE_FULL_BODY_STANDING"},
                {"anchor_id": "ANCHOR_POSE_WALKING_SIDE"},
            ]
        },
        "render_plan": [
            {
                "shot_id": "S001",
                "selected_pose_anchor_id": "ANCHOR_POSE_FULL_BODY_STANDING",
                "pose_action_need": {"world_interaction": "source-bound movement through established world"},
            },
            {
                "shot_id": "S002",
                "selected_pose_anchor_id": "ANCHOR_POSE_WALKING_SIDE",
                "pose_action_need": {"world_interaction": "tending source-bound seedlings or plants"},
            },
            {
                "shot_id": "S003",
                "selected_pose_anchor_id": "ANCHOR_POSE_WALKING_SIDE",
                "pose_action_need": {"world_interaction": "tending source-bound seedlings or plants"},
            },
        ],
    }

    audit = audit_pose_keyframe_diversity(preview)

    assert audit["pose_action_need_world_interaction_counts"] == {
        "source-bound movement through established world": 1,
        "tending source-bound seedlings or plants": 2,
    }
    assert audit["rows"][1]["pose_action_need_world_interaction"] == "tending source-bound seedlings or plants"


def test_pose_keyframe_diversity_audit_enriches_rows_from_shot_plan_and_extracts_still_camera():
    preview = {
        "workflow_prompt_lint": {"status": "pass"},
        "shot_plan": [
            {
                "shot_id": "S001",
                "section_type": "intro",
                "story_function": "world_bridge",
                "visual_mode": "establishing_wide",
            }
        ],
        "anchor_package": {"pose_anchor_bank": [{"anchor_id": "ANCHOR_POSE_FULL_BODY_STANDING"}]},
        "render_plan": [
            {
                "shot_id": "S001",
                "candidate_role": "world_bridge",
                "selected_pose_anchor_id": "ANCHOR_POSE_FULL_BODY_STANDING",
                "workflow_prompts": {
                    "flux2_ref_still": {
                        "positive_text": "Use the reference image as the character identity source. medium-wide cinematic composition, source world continuity. Only change the background."
                    }
                },
            }
        ],
    }

    audit = audit_pose_keyframe_diversity(preview)

    assert audit["rows"][0]["section_type"] == "intro"
    assert audit["rows"][0]["story_function"] == "world_bridge"
    assert audit["rows"][0]["visual_mode"] == "establishing_wide"
    assert audit["rows"][0]["still_camera"] == "medium-wide cinematic composition"
