from ai_mv.core.artifacts.publish import write_pipeline_artifacts
from ai_mv.core.artifacts.manifest import write_manifest


def test_write_manifest_includes_schema_version_and_required_root_sections(monkeypatch):
    captured = []

    monkeypatch.setattr("ai_mv.core.artifacts.manifest.write_json", lambda path, payload: captured.append((str(path), payload)))
    monkeypatch.setattr("ai_mv.core.artifacts.manifest.run_file", lambda run_id, name, scope: f"/tmp/{run_id}/{scope}/{name}")
    monkeypatch.setattr("ai_mv.core.artifacts.manifest.latest_file", lambda name, scope: f"/tmp/latest/{scope}/{name}")
    monkeypatch.setattr("ai_mv.core.artifacts.manifest.latest_success_file", lambda name, scope: f"/tmp/latest-success/{scope}/{name}")

    write_manifest(
        {"run_id": "run-200", "status": "done", "failure_reason": "", "scope": "run"},
        {
            "concept_text": "citypop night drive",
            "music_file": "music.mp3",
            "audio_plan": {"genre_description": "citypop"},
            "audio_map": {"sections": [{"name": "verse"}]},
            "style_name": "citypop",
            "style_resolution": {"style_name": "citypop", "selection_source": "auto"},
            "shot_plan": [{"shot_id": "S001"}],
            "render_plan": [{"shot_id": "S001", "render_mode": "i2v"}],
            "still_results": [{"shot_id": "S001", "image": "stills/S001.png"}],
            "clip_results": [{"shot_id": "S001", "video": "clips/S001.mp4"}],
            "review_report": {"status": "done", "rerender_targets": []},
            "final_video": "final.mp4",
            "review_inputs": {"music_file": "music.mp3"},
        },
    )

    manifest = captured[0][1]
    assert manifest["schema_version"] == "ai_mv_schema_v1"
    assert manifest["input"] == {"concept_text": "citypop night drive"}
    assert manifest["song"] == {
        "music_file": "music.mp3",
        "audio_plan": {"genre_description": "citypop"},
        "audio_map": {"sections": [{"name": "verse"}]},
    }
    assert manifest["style_resolution"] == {"style_name": "citypop", "selection_source": "auto"}
    assert manifest["sections"] == [{"shot_id": "S001"}]
    assert manifest["materials"] == {"still_results": [{"shot_id": "S001", "image": "stills/S001.png"}]}
    assert manifest["renders"] == {
        "render_plan": [{"shot_id": "S001", "render_mode": "i2v"}],
        "clip_results": [{"shot_id": "S001", "video": "clips/S001.mp4"}],
    }
    assert manifest["assembly"] == {
        "final_video": "final.mp4",
        "review_inputs": {"music_file": "music.mp3"},
    }
    assert manifest["review"] == {"status": "done", "rerender_targets": []}
    assert manifest["artifacts"] == {"scope": "run"}



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
