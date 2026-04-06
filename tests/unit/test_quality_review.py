from ai_mv.core.artifacts.paths import latest_file, latest_success_file, run_file
from ai_mv.core.artifacts.quality_review import write_quality_review
from ai_mv.core.artifacts.run_summary import write_run_summary
from ai_mv.core.quality_review import build_quality_review, build_run_summary


def test_run_summary_and_quality_review_are_written(tmp_path, monkeypatch):
    monkeypatch.setattr("ai_mv.core.artifacts.paths.PROJECT_ROOT", tmp_path)
    state = {"run_id": "r1", "status": "done", "completed_stages": ["audio"], "current_stage": "done", "failure_reason": ""}
    payload = {
        "selected_brief": "director_brief_example",
        "audio_map": {"language": "ko", "sections": [{"name": "intro", "label": "Intro"}]},
        "scene_outline": {"shot_packages": []},
    }
    review = {"reasoning": "minimal", "strengths": [], "risks": [], "metrics": {}}
    summary = build_run_summary(state, payload, review)
    write_quality_review(state, review)
    write_run_summary(state, summary)
    assert run_file("r1", "quality_review.json").exists()
    assert run_file("r1", "run_summary.json").exists()
    assert latest_file("quality_review.json").exists()
    assert latest_file("run_summary.json").exists()
    assert latest_success_file("quality_review.json").exists()
    assert latest_success_file("run_summary.json").exists()


def test_run_summary_includes_minimal_plan_metrics():
    state = {"run_id": "r7", "status": "done", "completed_stages": [], "current_stage": "done", "failure_reason": ""}
    payload = {
        "selected_brief": "director_brief_example",
        "audio_map": {"language": "ko", "sections": [{"name": "intro", "label": "Intro"}]},
        "scene_outline": {
            "shot_packages": [
                {"shot_id": "b1", "section_label": "Intro", "world_zone": "threshold", "story_function": "entry"},
                {"shot_id": "b2", "section_label": "Chorus", "world_zone": "open_peak", "story_function": "payoff"},
            ]
        },
        "direction_plan": {"shot_packages": [{"shot_id": "b1", "ref_archetype": "gate_pass"}, {"shot_id": "b2", "ref_archetype": "curb_crossing"}]},
        "prompt_plan": {"ref_items": [{"shot_id": "b1"}, {"shot_id": "b2"}]},
    }
    summary = build_run_summary(state, payload, {})
    assert summary["pipeline_version"] == "minimal"
    assert summary["shot_package_count"] == 2
    assert summary["world_zone_count"] == 2
    assert summary["story_function_count"] == 2
    assert summary["archetype_count"] == 2
    assert "repeated_hook_variation" not in summary


def test_quality_review_is_minimal_and_runtime_focused():
    payload = {
        "lyrics_timeline": {
            "sections": [
                {"section_label": "Intro", "lines": [{"line_index": 1, "text": "a"}], "lyric_beats": [{"beat_id": "intro_b1", "line_refs": [1]}]},
                {"section_label": "Chorus", "lines": [{"line_index": 1, "text": "b"}], "lyric_beats": [{"beat_id": "chorus_b1", "line_refs": [1]}]},
            ]
        },
        "scene_outline": {
            "shot_packages": [
                {"shot_id": "intro_b1", "section_label": "Intro", "world_zone": "threshold", "story_function": "entry", "beat_refs": ["intro_b1"], "line_refs": [1]},
                {"shot_id": "chorus_b1", "section_label": "Chorus", "world_zone": "open_peak", "story_function": "payoff", "beat_refs": ["chorus_b1"], "line_refs": [1]},
            ]
        },
        "clip_routes": [{"shot_id": "chorus_b1", "section_label": "Chorus", "use_ref": True}],
    }
    out = build_quality_review({}, payload)
    assert out["reasoning"]
    assert "metrics" in out
    assert out["metrics"]["shot_package_count"] == 2
    assert out["metrics"]["lyric_beat_count"] == 2
