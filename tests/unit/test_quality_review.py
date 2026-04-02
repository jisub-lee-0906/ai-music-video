from ai_mv.core.artifacts.paths import latest_file, latest_success_file, run_file
from ai_mv.core.artifacts.quality_review import write_quality_review
from ai_mv.core.artifacts.run_summary import write_run_summary
from ai_mv.core.quality_review import build_quality_review, build_run_summary


def test_run_summary_and_quality_review_are_written(tmp_path, monkeypatch):
    monkeypatch.setattr("ai_mv.core.artifacts.paths.PROJECT_ROOT", tmp_path)
    state = {"run_id": "r1", "status": "done", "completed_stages": ["acestep_music"], "current_stage": "done", "failure_reason": ""}
    payload = {
        "selected_brief": "director_brief_example",
        "audio_map": {"language": "ko", "sections": [{"name": "intro", "label": "Intro"}]},
        "scene_plan_v2": {"shot_packages": []},
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


def test_run_summary_includes_v2_plan_metrics():
    state = {"run_id": "r7", "status": "done", "completed_stages": [], "current_stage": "done", "failure_reason": ""}
    payload = {
        "selected_brief": "director_brief_example",
        "audio_map": {"language": "ko", "sections": [{"name": "intro", "label": "Intro"}]},
        "scene_plan_v2": {
            "shot_packages": [
                {"shot_id": "B001", "section_label": "Intro", "zone": "threshold", "motif_family": "train window", "continuity_group": "Intro:threshold"},
                {"shot_id": "B002", "section_label": "Chorus", "zone": "open_world", "motif_family": "ticket gate", "continuity_group": "Chorus:open_world"},
            ]
        },
        "render_plan_v2": {
            "shot_packages": [
                {"shot_id": "B001", "render_strategy": "ref_pair"},
                {"shot_id": "B002", "render_strategy": "ref_pair"},
            ]
        },
    }
    summary = build_run_summary(state, payload, {})
    assert summary["pipeline_version"] == "v2"
    assert summary["shot_package_count"] == 2
    assert summary["motif_family_count"] == 2
    assert summary["zone_count"] == 2
    assert summary["continuity_group_count"] == 2
    assert summary["render_strategy_counts"] == {"ref_pair": 2}


def test_quality_review_v2_uses_scene_director_inputs():
    payload = {
        "lyrics_timeline": {
            "sections": [
                {"section_label": "Intro", "lyric_beats": [{"beat_id": "B001"}]},
                {"section_label": "Chorus", "lyric_beats": [{"beat_id": "B002"}]},
            ]
        },
        "scene_plan_v2": {
            "identity_core": "same Korean female idol",
            "world_core": "late-night city transit spaces",
            "zone_progression": [
                {"section_label": "Intro", "zone": "threshold", "story_role": "threshold setup"},
                {"section_label": "Chorus", "zone": "open_world", "story_role": "open world release"},
            ],
            "motif_progression": [
                {"shot_id": "B001", "motif_family": "train window"},
                {"shot_id": "B002", "motif_family": "ticket gate"},
            ],
            "shot_packages": [
                {"shot_id": "B001", "section_label": "Intro", "zone": "threshold", "motif_family": "train window", "continuity_group": "Intro:threshold", "identity_core": "same Korean female idol", "beat_refs": ["B001"], "line_refs": [1], "visual_role": "opening_frame"},
                {"shot_id": "B002", "section_label": "Chorus", "zone": "open_world", "motif_family": "ticket gate", "continuity_group": "Chorus:open_world", "identity_core": "same Korean female idol", "beat_refs": ["B002"], "line_refs": [1], "visual_role": "payoff_frame"},
            ],
        },
        "director_plan_v2": {
            "shot_packages": [
                {"shot_id": "B001", "section_label": "Intro", "zone": "threshold", "camera_intent": "favor objects and space before direct face coverage", "identity_core": "same Korean female idol", "visual_role": "opening_frame"},
                {"shot_id": "B002", "section_label": "Chorus", "zone": "open_world", "camera_intent": "open the frame wider and let the camera commit to the payoff space", "identity_core": "same Korean female idol", "visual_role": "payoff_frame"},
            ]
        },
        "render_plan_v2": {
            "shot_packages": [
                {"shot_id": "B001", "render_strategy": "ref_pair", "identity_core": "same Korean female idol", "visual_role": "opening_frame"},
                {"shot_id": "B002", "render_strategy": "ref_pair", "identity_core": "same Korean female idol", "visual_role": "payoff_frame"},
            ]
        },
        "backend_preview_v2": {
            "ref_adapter_v2": [
                {
                    "raw_prompt_clauses": {
                        "primary_surface": "threshold",
                        "ref_archetype": "threshold_crossing",
                        "start_state": "She crosses the threshold",
                        "end_state": "She lands beyond the threshold",
                    },
                    "start_prompt_preview": "The same Korean female idol crosses the threshold into the wet street.",
                    "end_prompt_preview": "The same Korean female idol lands beyond the threshold and keeps moving.",
                }
            ],
            "wan_adapter_v2": [
                {
                    "raw_prompt_clauses": {"bridge_action": "She clears the threshold and keeps going", "ref_archetype": "threshold_crossing"},
                    "positive_prompt_preview": "The same Korean female idol clears the threshold and keeps going into the wet street.",
                    "start_source": "ref_start",
                },
                {
                    "raw_prompt_clauses": {"bridge_action": "She keeps moving across the wet street edge", "ref_archetype": "sidewalk_continuation"},
                    "positive_prompt_preview": "The same Korean female idol keeps moving across the wet street edge.",
                    "start_source": "previous_end",
                },
            ]
        },
    }
    out = build_quality_review({}, payload)
    assert out["story_progression"]["strengths"]
    assert out["profile_continuity"]["strengths"]
    assert out["style_alignment"]["strengths"]
    assert out["ref_prompt_contracts"]["metrics"]["subject_first_ratio"] > 0
    assert out["wan_prompt_contracts"]["metrics"]["bridge_integrity_ratio"] > 0
