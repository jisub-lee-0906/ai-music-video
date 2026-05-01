from ai_mv.core.planning.render_priority import build_render_planning


def test_build_render_planning_emits_appendix_priority_scores_for_chorus_peak():
    out = build_render_planning(
        "synthwave",
        {
            "energy": "high",
            "section_type": "chorus",
            "framing_intent": "performance_medium",
            "visual_mode": "chorus_performance",
            "continuity_mode": "strict",
        },
    )

    assert out == {
        "section_energy_score": 0.75,
        "section_emphasis_score": 1.0,
        "mode_importance_score": 1.0,
        "lane_priority_score": 0.85,
        "continuity_need_score": 1.0,
        "render_priority_score": 0.9,
    }


def test_build_render_planning_defaults_non_priority_lane_and_medium_continuity():
    out = build_render_planning(
        "citypop",
        {
            "energy": "release",
            "section_type": "outro",
            "framing_intent": "release_wide",
            "visual_mode": "neon_release",
            "continuity_mode": "medium",
        },
    )

    assert out == {
        "section_energy_score": 0.55,
        "section_emphasis_score": 0.72,
        "mode_importance_score": 0.72,
        "lane_priority_score": 0.7,
        "continuity_need_score": 0.5,
        "render_priority_score": 0.64,
    }
