from ai_mv.core.artifacts.run_summary import write_run_summary
from ai_mv.core.artifacts.quality_review import write_quality_review
from ai_mv.core.artifacts.paths import latest_file, run_file
from ai_mv.core.quality_review import build_quality_review, build_run_summary


def test_build_quality_review_carries_audio_and_visual_reviews(monkeypatch):
    monkeypatch.setattr(
        "ai_mv.core.quality_review.generate_structured",
        lambda _config, _prompt, _schema: {
            "reasoning": "Coverage is coherent and editable.",
            "strengths": ["same-world continuity", "clear progression"],
            "risks": ["bridge still a bit safe"],
        },
    )
    payload = {
        "selected_profile": "jpop_citypop",
        "audio_map": {"profile_summary": "city-pop", "language": "ja"},
        "visual_brief": {
            "section_briefs": [
                {"section_name": "intro", "story_beat": "checks the reflection", "location_anchor": "station glass", "emotional_arc": "searching"}
            ]
        },
        "workflow_inputs_preview": {
            "tti_anchor": {"master_anchor": {"prompt_text": "night city heroine"}},
            "uso_chain": {"items": [{"shot_id": "S001", "clip_phase": "establish", "space_relation": "glass camera-right", "start_text": "a", "end_text": "b"}]},
            "wan_interpolation": {"clips": [{"shot_id": "S001", "energy": "normal", "space_relation": "glass camera-right", "positive_prompt": "walks through"}]},
        },
    }
    out = build_quality_review({}, payload)
    assert out["visual"]["reasoning"] == "Coverage is coherent and editable."


def test_run_summary_and_quality_review_are_written(tmp_path, monkeypatch):
    monkeypatch.setattr("ai_mv.core.artifacts.paths.PROJECT_ROOT", tmp_path)
    state = {"run_id": "r1", "completed_stages": ["acestep_music"], "current_stage": "done", "failure_reason": ""}
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
