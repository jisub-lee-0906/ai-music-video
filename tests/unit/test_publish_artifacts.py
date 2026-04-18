from ai_mv.core.artifacts.publish import write_pipeline_artifacts


def test_write_pipeline_artifacts_includes_rerender_escalation_summary(monkeypatch):
    captured = {}
    monkeypatch.setattr("ai_mv.core.artifacts.publish.write_manifest", lambda state, payload: None)
    monkeypatch.setattr("ai_mv.core.artifacts.publish.write_run_summary", lambda state, summary: captured.update(summary))

    write_pipeline_artifacts(
        {"run_id": "run-123", "status": "done", "current_stage": "escalation", "completed_stages": ["review", "rerender", "escalation"]},
        {
            "concept_text": "citypop night drive",
            "final_video": "final.mp4",
            "music_file": "music.mp3",
            "review_report": {"status": "needs_rerender", "rerender_targets": ["S001"]},
            "rerender_escalation": {
                "status": "manual_review_required",
                "shot_count": 1,
                "reviewer_summary": "Manual review required for 1 shots: S001",
                "summary_by_shot": [
                    {
                        "shot_id": "S001",
                        "reason_codes": ["continuity_break"],
                        "priority_score": 7,
                        "recommended_action": "rerender_continuity_break_shots",
                    }
                ],
            },
        },
        {},
    )

    assert captured["rerender_escalation_status"] == "manual_review_required"
    assert captured["rerender_escalation_shot_count"] == 1
    assert captured["rerender_escalation_reviewer_summary"] == "Manual review required for 1 shots: S001"
    assert captured["rerender_escalation_shot_ids"] == ["S001"]
    assert captured["rerender_escalation_actions"] == ["rerender_continuity_break_shots"]
