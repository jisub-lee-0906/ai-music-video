from ai_mv.core.visual_pipeline import (
    attach_tti_metadata,
    build_section_semantics,
    build_clip_routes,
)


def test_build_section_semantics_marks_final_chorus_as_peak():
    sections = [
        {"name": "verse_1", "label": "Verse 1"},
        {"name": "chorus", "label": "Final Chorus"},
    ]
    out = build_section_semantics({}, sections)
    assert out[0]["release_level"] == "low"
    assert out[1]["release_level"] == "peak"
    assert out[1]["hero_frame_priority"] == "peak"


def test_attach_tti_metadata_scores_emotion_close_as_consistency_heavy():
    shot = attach_tti_metadata(
        {
            "shot_type": "EMOTION_CLOSE",
        },
        "chorus",
        "Final Chorus",
    )
    assert shot["mv_function"] == "payoff"
    assert shot["hero_frame_score"] >= 4
    assert shot["consistency_need"] == "high"
    assert shot["edit_density"] == "high"
    assert shot["shot_priority"] == "hero"
    assert shot["transition_role"] == "arrival"


def test_build_clip_routes_selects_ref_for_final_chorus_emotion_close():
    cfg = {"video": {"target": "1920x1080@24"}}
    anchors = [
        {
            "shot_id": "S010",
            "anchor": "master.png",
            "identity_anchor": "master.png",
            "duration_sec": 4.0,
            "section_name": "chorus",
            "section_label": "Final Chorus",
            "shot_type": "EMOTION_CLOSE",
            "camera_language": "clean frame",
            "pose_delta": "small turn",
            "emotion": "lift",
            "scene_detail": "rain glow",
            "motion_hint": "slow move",
            "space_relation": "glass stays camera-right",
            "hero_frame_score": 5,
            "consistency_need": "high",
            "mv_function": "payoff",
            "return_weight": 4,
        }
    ]
    routes = build_clip_routes(cfg, anchors)
    assert routes[0]["use_ref"] is True
    assert routes[0]["route_reason"] == "priority return hero"


def test_build_clip_routes_selective_ref_uses_priority_return_edges_not_all_parts():
    cfg = {"video": {"target": "1920x1080@24"}}
    anchors = [
        {
            "shot_id": "S010",
            "anchor": "master.png",
            "identity_anchor": "master.png",
            "duration_sec": 12.0,
            "section_name": "chorus",
            "section_label": "Final Chorus",
            "shot_type": "PERF_WIDE",
            "camera_language": "clean frame",
            "pose_delta": "small turn",
            "emotion": "lift",
            "scene_detail": "rain glow",
            "motion_hint": "slow move",
            "space_relation": "glass stays camera-right",
            "hero_frame_score": 3,
            "consistency_need": "normal",
            "mv_function": "payoff",
            "return_weight": 4,
        }
    ]
    routes = build_clip_routes(cfg, anchors)
    assert routes[0]["use_ref"] is True
    assert routes[-1]["use_ref"] is True
    assert any(route["use_ref"] is False for route in routes[1:-1])
