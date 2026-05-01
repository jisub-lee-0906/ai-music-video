from ai_mv.core.planning.reference_policy import build_reference_policy, build_variation_delta_contract


def test_build_reference_policy_marks_performance_anchor_sources():
    out = build_reference_policy(
        {
            "shot_id": "S010",
            "shot_role": "chorus_arrive",
            "coverage_role": "anchor",
            "workflow_intent": "audio_reactive_candidate",
            "section_type": "chorus",
            "visual_mode": "chorus_performance",
            "framing_intent": "performance_medium",
            "continuity_contract": {
                "protagonist_anchor": "same lead performer",
                "world_anchor": "same glossy performance-night stage",
            },
        }
    )

    assert out == {
        "reference_mode": "performance_anchor_source",
        "reference_source_shot_id": "S010",
        "identity_lock_strength": "performance_anchor",
    }


def test_build_variation_delta_contract_prefers_bridge_reframe_for_anchor_followups():
    policy = {
        "reference_mode": "use_anchor_still",
        "reference_source_shot_id": "S001",
        "identity_lock_strength": "high",
    }

    out = build_variation_delta_contract(
        {
            "shot_id": "S020",
            "shot_role": "bridge_escape",
            "section_type": "bridge",
            "visual_mode": "bridge_close_gloss",
        },
        policy,
    )

    assert out == {
        "edit_variation_scope": "bridge_reframe",
        "minimum_visual_delta": "lighting_or_framing_change_required",
    }
