from ai_mv.core.artifacts.run_summary import write_run_summary
from ai_mv.core.artifacts.quality_review import write_quality_review
from ai_mv.core.artifacts.paths import latest_file, latest_success_file, run_file
from ai_mv.core.quality_review import build_quality_review, build_run_summary
from ai_mv.engines.wan_2_2_flf2v.planner import _compose_positive_prompt


def test_build_quality_review_carries_audio_and_visual_reviews(monkeypatch):
    payload = {
        "selected_profile": "jpop_citypop",
        "audio_map": {"profile_summary": "city-pop", "language": "ja"},
        "lyrics_timeline": {
            "sections": [
                {"section_name": "intro", "section_label": "Intro", "lines": [{"line_index": 1, "text": "glass"}], "hook_lines": [], "lyric_beats": [{"beat_id": "LB01_01", "line_refs": [1], "visible_action": "checks the reflection", "payoff_role": "entry"}]}
            ]
        },
        "visual_story_bible": {
            "hero_identity_lock": "hero",
            "world_rules": "world",
            "recurring_location_families": ["station glass"],
            "forbidden_drift": ["drift"],
            "lyric_beats": [
                {"beat_id": "LB01_01", "section_name": "intro", "section_label": "Intro", "line_refs": [1], "literal_image": "glass", "visible_action": "checks the reflection", "emotional_turn": "searching", "continuity_anchor": "gaze shift", "payoff_role": "entry", "repeat_variant_of": "", "location_family": "station glass", "palette_hint": "blue", "lighting_hint": "soft", "camera_commitment": "still"}
            ],
            "section_progression": [{"section_name": "intro", "section_label": "Intro", "dominant_emotion": "searching", "story_function": "entry", "lyric_beat_ids": ["LB01_01"]}],
            "repeat_escalation_rules": ["repeats vary"],
        },
        "shot_timeline": {"shots": [{"lyric_beat_id": "LB01_01"}]},
        "workflow_inputs_preview": {
            "shot_timeline": {"master_anchor": {"prompt_text": "night city heroine"}},
            "shot_router": {"decisions": [{"shot_id": "S001", "use_ref": True, "reason": "hero shot type", "mv_function": "payoff", "clip_phase": "establish", "shot_priority": "hero"}]},
            "flux2_ref_chain": {"items": [{"shot_id": "S001", "clip_phase": "establish", "space_relation": "glass camera-right", "start_text": "a", "end_text": "b"}]},
            "wan_interpolation": {"clips": [{"shot_id": "S001", "energy": "normal", "space_relation": "glass camera-right", "positive_prompt": "walks through"}]},
        },
        "clip_routes": [{"shot_id": "S001", "section_label": "Final Chorus", "use_ref": True}],
    }
    out = build_quality_review({}, payload)
    assert out["visual"]["reasoning"]
    assert out["visual"]["strengths"]


def test_run_summary_and_quality_review_are_written(tmp_path, monkeypatch):
    monkeypatch.setattr("ai_mv.core.artifacts.paths.PROJECT_ROOT", tmp_path)
    state = {"run_id": "r1", "status": "done", "completed_stages": ["acestep_music"], "current_stage": "done", "failure_reason": ""}
    payload = {
        "selected_profile": "jpop_citypop",
        "audio_map": {
            "language": "ja",
            "sections": [{"name": "intro", "label": "Intro"}, {"name": "chorus", "label": "Final Chorus"}],
        },
    }
    review = {"visual": {"reasoning": "best"}}
    summary = build_run_summary(state, payload, review)
    write_quality_review(state, review)
    write_run_summary(state, summary)
    assert run_file("r1", "quality_review.json").exists()
    assert run_file("r1", "run_summary.json").exists()
    assert latest_file("quality_review.json").exists()
    assert latest_file("run_summary.json").exists()
    assert latest_success_file("quality_review.json").exists()
    assert latest_success_file("run_summary.json").exists()


def test_run_summary_includes_route_counts():
    state = {"run_id": "r3", "status": "done", "completed_stages": [], "current_stage": "done", "failure_reason": ""}
    payload = {
        "selected_profile": "jpop_citypop",
        "audio_map": {
            "language": "ja",
            "sections": [{"name": "chorus", "label": "Final Chorus"}],
        },
        "clip_routes": [
            {"shot_id": "S001", "section_label": "Final Chorus", "use_ref": True},
            {"shot_id": "S002", "section_label": "Final Chorus", "use_ref": False},
        ],
    }
    summary = build_run_summary(state, payload, {})
    assert summary["tti_only_count"] == 1
    assert summary["ref_assisted_count"] == 1
    assert summary["ref_ratio_by_section"]["Final Chorus"] == 0.5


def test_run_summary_failure_does_not_overwrite_latest_success(tmp_path, monkeypatch):
    monkeypatch.setattr("ai_mv.core.artifacts.paths.PROJECT_ROOT", tmp_path)
    success_state = {"run_id": "r1", "status": "done", "completed_stages": [], "current_stage": "done", "failure_reason": ""}
    failed_state = {"run_id": "r2", "status": "failed", "completed_stages": ["acestep_music"], "current_stage": "wan_interpolation", "failure_reason": "boom"}
    summary = {"run_id": "r1"}
    failed_summary = {"run_id": "r2"}

    write_run_summary(success_state, summary)
    write_run_summary(failed_state, failed_summary)

    assert latest_file("run_summary.json").exists()
    assert latest_success_file("run_summary.json").exists()
    assert latest_success_file("run_summary.json").read_text(encoding="utf-8").find('"run_id": "r1"') >= 0


def test_wan_compose_prefers_environment_sentence_when_camera_relation_is_static():
    text = _compose_positive_prompt(
        {
            "subject_motion": "She moves through the lane and lifts her eyes toward the station light",
            "camera_relation": "holds a close side profile",
            "environment_detail": "Wet stripes brighten underfoot",
        }
    )
    assert text == "She moves through the lane and lifts her eyes toward the station light. Wet stripes brighten underfoot."


def test_wan_compose_keeps_relation_phrase_without_forcing_camera_prefix():
    text = _compose_positive_prompt(
        {
            "subject_motion": "She continues across the crossing with a calmer stride",
            "camera_relation": "glides backward in front of her",
            "environment_detail": "Wet lane marks flare softly",
        }
    )
    assert text == "She continues across the crossing with a calmer stride. Glides backward in front of her, while wet lane marks flare softly."


def test_wan_compose_prefers_environment_when_relation_uses_technical_subject():
    text = _compose_positive_prompt(
        {
            "subject_motion": "She keeps walking and lets her gaze return forward",
            "camera_relation": "the track settles beside her",
            "environment_detail": "wet pavement glow slips under the glass line",
        }
    )
    assert text == "She keeps walking and lets her gaze return forward. Wet pavement glow slips under the glass line."


def test_wan_compose_naturalizes_keep_centered_relation():
    text = _compose_positive_prompt(
        {
            "subject_motion": "She eases toward stillness by the storefront and lets her eyes fall down the empty sidewalk",
            "camera_relation": "a quiet backward glide keeps her centered",
            "environment_detail": "open pavement extends on camera-right",
        }
    )
    assert text == "She eases toward stillness by the storefront and lets her eyes fall down the empty sidewalk. A quiet backward glide stays centered on her, while open pavement extends on camera-right."


def test_wan_compose_naturalizes_gives_her_space_relation():
    text = _compose_positive_prompt(
        {
            "subject_motion": "She carries forward with a measured stride and a faint shoulder release",
            "camera_relation": "a steady glide gives her space",
            "environment_detail": "teal and amber glow trail behind her",
        }
    )
    assert text == "She carries forward with a measured stride and a faint shoulder release. A steady glide gives her a little space, while teal and amber glow trail behind her."
