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
                "artifacts": {
                    "review_packet_manifest": "review-packet.json",
                    "quality_findings": "review-findings.json",
                    "reviewer_notes": "review-notes.md",
                },
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
    assert captured["rerender_escalation_max_priority"] == 7
    assert captured["rerender_escalation_unique_actions"] == ["rerender_continuity_break_shots"]
    assert captured["rerender_escalation_reason_codes"] == ["continuity_break"]
    assert captured["rerender_escalation_unique_reason_codes"] == ["continuity_break"]
    assert captured["rerender_escalation_artifact_keys"] == ["quality_findings", "review_packet_manifest", "reviewer_notes"]
    assert captured["rerender_escalation_review_packet_manifest"] == "review-packet.json"
    assert captured["rerender_escalation_quality_findings_path"] == "review-findings.json"
    assert captured["rerender_escalation_reviewer_notes_path"] == "review-notes.md"


def test_write_pipeline_artifacts_handles_not_required_rerender_escalation(monkeypatch):
    captured = {}
    monkeypatch.setattr("ai_mv.core.artifacts.publish.write_manifest", lambda state, payload: None)
    monkeypatch.setattr("ai_mv.core.artifacts.publish.write_run_summary", lambda state, summary: captured.update(summary))

    write_pipeline_artifacts(
        {"run_id": "run-124", "status": "done", "current_stage": "review", "completed_stages": ["review"]},
        {
            "concept_text": "citypop night drive",
            "final_video": "final.mp4",
            "music_file": "music.mp3",
            "review_report": {"status": "done", "rerender_targets": []},
            "rerender_escalation": {
                "status": "not_required",
                "shot_ids": [],
                "shot_count": 0,
                "summary_by_shot": [],
                "video_path": "final.mp4",
                "reviewer_summary": "No manual review required",
                "artifacts": {},
            },
        },
        {},
    )

    assert captured["rerender_escalation_status"] == "not_required"
    assert captured["rerender_escalation_shot_count"] == 0
    assert captured["rerender_escalation_reviewer_summary"] == "No manual review required"
    assert captured["rerender_escalation_shot_ids"] == []
    assert captured["rerender_escalation_actions"] == []
    assert captured["rerender_escalation_max_priority"] == 0
    assert captured["rerender_escalation_unique_actions"] == []
    assert captured["rerender_escalation_reason_codes"] == []
    assert captured["rerender_escalation_unique_reason_codes"] == []
    assert captured["rerender_escalation_artifact_keys"] == []
