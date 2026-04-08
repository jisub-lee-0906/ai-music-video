from ai_mv.core.artifacts.paths import latest_file, latest_success_file, run_file
from ai_mv.core.artifacts.llm_review import write_llm_review
from ai_mv.core.artifacts.quality_review import write_quality_review
from ai_mv.core.artifacts.run_summary import write_run_summary
from ai_mv.core.contracts.errors import CodexCliRequestError
from ai_mv.core.quality_review import build_quality_review, build_run_summary
from ai_mv.core.llm_review import build_llm_review


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


def test_llm_review_is_written(tmp_path, monkeypatch):
    monkeypatch.setattr("ai_mv.core.artifacts.paths.PROJECT_ROOT", tmp_path)
    state = {"run_id": "r2", "status": "done", "completed_stages": ["merge"], "current_stage": "done", "failure_reason": ""}
    review = {
        "summary": "usable",
        "overall_verdict": "usable",
        "strengths": ["good continuity"],
        "concerns": ["needs stronger ref variety"],
        "next_focus": ["review wan transitions"],
        "stage_notes": {"audio": "ok", "tti": "ok", "ref": "mixed", "wan": "ok", "final_mv": "mixed"},
    }
    write_llm_review(state, review)
    assert run_file("r2", "llm_review.json").exists()
    assert latest_file("llm_review.json").exists()
    assert latest_success_file("llm_review.json").exists()


def test_build_llm_review_returns_fallback_when_cli_fails(monkeypatch):
    monkeypatch.setattr(
        "ai_mv.core.llm_review.generate_structured",
        lambda *args, **kwargs: (_ for _ in ()).throw(CodexCliRequestError("boom")),
    )
    review = build_llm_review(
        {"review": {"llm_review": True}},
        {"audio_plan": {}, "audio_map": {}, "prompt_plan": {}},
    )
    assert review["overall_verdict"] == "mixed"
    assert "LLM review could not be generated" in review["summary"]


def test_run_summary_includes_minimal_plan_metrics():
    state = {"run_id": "r7", "status": "done", "completed_stages": [], "current_stage": "done", "failure_reason": ""}
    payload = {
        "selected_brief": "director_brief_example",
        "audio_map": {
            "language": "ko",
            "duration_sec": 10.0,
            "sections": [{"name": "intro", "label": "Intro"}],
        },
        "lyrics_timeline": {
            "sections": [
                {
                    "section_label": "Intro",
                    "lines": [{"line_index": 1, "text": "a"}],
                    "lyric_beats": [{"beat_id": "intro_b1", "line_refs": [1], "start_sec": 0.0, "end_sec": 2.0}],
                }
            ]
        },
        "scene_outline": {
            "shot_packages": [
                {"shot_id": "b1", "section_label": "Intro", "payoff_role": "setup", "beat_refs": ["intro_b1"], "line_refs": [1]},
                {"shot_id": "b2", "section_label": "Chorus", "payoff_role": "release", "beat_refs": ["intro_b1"], "line_refs": [1]},
            ]
        },
        "direction_plan": {"shot_packages": [{"shot_id": "b1", "shot_function": "setup", "place": "diner"}, {"shot_id": "b2", "shot_function": "release", "place": "street"}]},
        "prompt_plan": {
            "ref_items": [
                {"shot_id": "b1", "ref_prompt_text": "The same performer walks through the diner. Keep the face.", "duration_sec": 3.0},
                {"shot_id": "b2", "ref_prompt_text": "The same performer reaches the street. Keep the face.", "duration_sec": 4.0},
            ],
            "wan_items": [
                {"shot_id": "b2", "wan_positive_prompt_text": "She moves forward through the cut.", "duration_sec": 4.0}
            ],
        },
        "audio_duration_sec": 10.0,
        "final_duration_sec": 10.0,
    }
    summary = build_run_summary(state, payload, {})
    assert summary["pipeline_version"] == "music_profile_centered_v1"
    assert summary["review_mode"] == "technical_signals_plus_llm_review"
    assert summary["shot_package_count"] == 2
    assert summary["payoff_role_count"] == 2
    assert summary["shot_function_count"] == 2
    assert summary["place_count"] == 2
    assert summary["beat_timing_monotonic"] is True
    assert summary["ref_item_count"] == 2
    assert summary["wan_item_count"] == 1
    assert summary["duration_drift_sec"] == 0.0


def test_quality_review_reports_runtime_alignment_and_prompt_health():
    payload = {
        "audio_duration_sec": 8.0,
        "final_duration_sec": 8.0,
        "lyrics_timeline": {
            "sections": [
                {"section_label": "Intro", "lines": [{"line_index": 1, "text": "a"}], "lyric_beats": [{"beat_id": "intro_b1", "line_refs": [1], "start_sec": 0.0, "end_sec": 2.0}]},
                {"section_label": "Chorus", "lines": [{"line_index": 1, "text": "b"}], "lyric_beats": [{"beat_id": "chorus_b1", "line_refs": [1], "start_sec": 2.0, "end_sec": 6.0}]},
            ]
        },
        "scene_outline": {
            "shot_packages": [
                {"shot_id": "intro_b1", "section_label": "Intro", "payoff_role": "setup", "beat_refs": ["intro_b1"], "line_refs": [1]},
                {"shot_id": "chorus_b1", "section_label": "Chorus", "payoff_role": "release", "beat_refs": ["chorus_b1"], "line_refs": [1]},
            ]
        },
        "prompt_plan": {
            "ref_items": [
                {"shot_id": "intro_b1", "ref_prompt_text": "The same performer stands by the window. Keep the face.", "duration_sec": 2.0},
                {"shot_id": "chorus_b1", "ref_prompt_text": "The same performer crosses the wet street. Keep the face.", "duration_sec": 4.0},
            ],
            "wan_items": [
                {"shot_id": "chorus_b1", "wan_positive_prompt_text": "She moves forward through the cut.", "duration_sec": 4.0}
            ],
        },
        "clip_routes": [{"shot_id": "chorus_b1", "section_label": "Chorus", "use_ref": True}],
    }
    out = build_quality_review({}, payload)
    assert out["reasoning"]
    assert "not the main creative evaluation" in out["reasoning"]
    assert "metrics" in out
    assert out["metrics"]["shot_package_count"] == 2
    assert out["metrics"]["lyric_beat_count"] == 2
    assert out["metrics"]["beat_timing_monotonic"] is True
    assert out["metrics"]["ref_adjacent_duplicate_count"] == 0
    assert out["metrics"]["wan_adjacent_duplicate_count"] == 0
    assert out["metrics"]["duration_drift_sec"] == 0.0
