from ai_mv.core.planning.routing import apply_render_routing


def test_routing_requires_audio_reactive_intent_for_ia2v_promotion():
    out = apply_render_routing(
        {
            "planning": {
                "enable_ia2v": True,
                "max_ia2v_shots": 1,
                "ia2v_min_sec": 4.0,
                "ia2v_max_sec": 8.0,
            }
        },
        [
            {
                "shot_id": "S001",
                "section_type": "chorus",
                "visual_mode": "chorus_performance",
                "duration_sec": 5.0,
                "render_mode": "i2v",
                "source_section_index": 1,
                "workflow_intent": "stable_i2v",
            }
        ],
    )

    assert out[0]["render_mode"] == "i2v"


def test_routing_can_promote_chorus_shot_to_ia2v():
    out = apply_render_routing(
        {
            "planning": {
                "enable_ia2v": True,
                "max_ia2v_shots": 1,
                "ia2v_min_sec": 4.0,
                "ia2v_max_sec": 8.0,
            }
        },
        [
            {
                "shot_id": "S001",
                "section_type": "chorus",
                "visual_mode": "chorus_performance",
                "duration_sec": 5.0,
                "render_mode": "i2v",
                "source_section_index": 1,
            }
        ],
    )

    assert out[0]["render_mode"] == "ia2v"


def test_routing_can_promote_bridge_to_flf2v_and_attach_target():
    out = apply_render_routing(
        {
            "planning": {
                "enable_flf2v": True,
                "max_flf2v_shots": 1,
                "flf2v_min_sec": 3.0,
                "flf2v_max_sec": 6.0,
            }
        },
        [
            {
                "shot_id": "S001",
                "section_type": "pre_chorus",
                "visual_mode": "city_glance",
                "duration_sec": 4.0,
                "render_mode": "i2v",
                "workflow_intent": "bridge_candidate",
            },
            {
                "shot_id": "S002",
                "section_type": "chorus",
                "visual_mode": "chorus_performance",
                "duration_sec": 5.0,
                "render_mode": "i2v",
                "workflow_intent": "audio_reactive_candidate",
            },
        ],
    )

    assert out[0]["render_mode"] == "flf2v"
    assert out[0]["bridge_to_shot_id"] == "S002"
    assert out[0]["shot_role"] == "bridge_transition"
    assert out[0]["visual_mode"] == "bridge_transition"


def test_routing_requires_bridge_intent_for_flf2v_promotion():
    out = apply_render_routing(
        {
            "planning": {
                "enable_flf2v": True,
                "max_flf2v_shots": 1,
                "flf2v_min_sec": 3.0,
                "flf2v_max_sec": 6.0,
            }
        },
        [
            {
                "shot_id": "S001",
                "section_type": "pre_chorus",
                "visual_mode": "city_glance",
                "duration_sec": 4.0,
                "render_mode": "i2v",
                "workflow_intent": "stable_i2v",
            },
            {
                "shot_id": "S002",
                "section_type": "chorus",
                "visual_mode": "chorus_performance",
                "duration_sec": 5.0,
                "render_mode": "i2v",
                "workflow_intent": "audio_reactive_candidate",
            },
        ],
    )

    assert out[0]["render_mode"] == "i2v"
    assert "bridge_to_shot_id" not in out[0]
