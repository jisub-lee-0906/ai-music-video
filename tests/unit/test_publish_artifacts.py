from ai_mv.core.artifacts import paths as artifact_paths
from ai_mv.core.artifacts.publish import write_pipeline_artifacts
from ai_mv.core.artifacts.manifest import write_manifest
from ai_mv.utils.json_utils import read_json


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



def test_write_manifest_falls_back_to_style_name_and_empty_safe_canonical_sections(monkeypatch):
    captured = []

    monkeypatch.setattr("ai_mv.core.artifacts.manifest.write_json", lambda path, payload: captured.append((str(path), payload)))
    monkeypatch.setattr("ai_mv.core.artifacts.manifest.run_file", lambda run_id, name, scope: f"/tmp/{run_id}/{scope}/{name}")
    monkeypatch.setattr("ai_mv.core.artifacts.manifest.latest_file", lambda name, scope: f"/tmp/latest/{scope}/{name}")
    monkeypatch.setattr("ai_mv.core.artifacts.manifest.latest_success_file", lambda name, scope: f"/tmp/latest-success/{scope}/{name}")

    write_manifest(
        {"run_id": "run-201", "status": "done", "failure_reason": "", "scope": "run"},
        {
            "concept_text": "dreamy dusk drive",
            "style_name": "dream_pop",
        },
    )

    manifest = captured[0][1]
    assert manifest["schema_version"] == "ai_mv_schema_v1"
    assert manifest["style_resolution"] == {"style_name": "dream_pop"}
    assert manifest["song"] == {"music_file": "", "audio_plan": {}, "audio_map": {}}
    assert manifest["sections"] == []
    assert manifest["materials"] == {"still_results": []}
    assert manifest["renders"] == {"render_plan": [], "clip_results": []}
    assert manifest["assembly"] == {"final_video": "", "review_inputs": {}}
    assert manifest["review"] == {}
    assert manifest["artifacts"] == {"scope": "run"}



def test_write_pipeline_artifacts_includes_schema_and_assembly_revision_in_run_summary(monkeypatch):
    captured = {}
    monkeypatch.setattr("ai_mv.core.artifacts.publish.write_manifest", lambda state, payload: None)
    monkeypatch.setattr("ai_mv.core.artifacts.publish.write_run_summary", lambda state, summary: captured.update(summary))

    write_pipeline_artifacts(
        {"run_id": "run-122", "status": "done", "current_stage": "publish", "completed_stages": ["plan", "review", "publish"]},
        {
            "concept_text": "citypop night drive",
            "style_name": "citypop",
            "style_resolution": {
                "style_name": "citypop",
                "selection_source": "auto",
                "selection_stability": "stable",
                "confidence": 0.93,
            },
            "final_video": "final.mp4",
            "music_file": "music.mp3",
            "review_report": {
                "status": "done",
                "rerender_targets": [],
                "assembly_revision_summary": {
                    "present": True,
                    "action": "revise_transition_selection",
                    "target": "assembly",
                    "final_video": "final.mp4",
                    "music_file": "music.mp3",
                },
            },
        },
        {},
    )

    assert captured["schema_version"] == "ai_mv_schema_v1"
    assert captured["style_name"] == "citypop"
    assert captured["style_selection_source"] == "auto"
    assert captured["style_selection_stability"] == "stable"
    assert captured["style_selection_confidence"] == 0.93
    assert captured["assembly_revision_present"] is True
    assert captured["assembly_revision_action"] == "revise_transition_selection"
    assert captured["assembly_revision_target"] == "assembly"
    assert captured["assembly_revision_final_video"] == "final.mp4"
    assert captured["assembly_revision_music_file"] == "music.mp3"



def test_write_pipeline_artifacts_sanitizes_invalid_style_selection_confidence(monkeypatch):
    captured = {}
    monkeypatch.setattr("ai_mv.core.artifacts.publish.write_manifest", lambda state, payload: None)
    monkeypatch.setattr("ai_mv.core.artifacts.publish.write_run_summary", lambda state, summary: captured.update(summary))

    write_pipeline_artifacts(
        {"run_id": "run-122b", "status": "done", "current_stage": "publish", "completed_stages": ["plan", "publish"]},
        {
            "concept_text": "citypop night drive",
            "style_name": "citypop",
            "style_resolution": {
                "style_name": "citypop",
                "selection_source": "auto",
                "selection_stability": "stable",
                "confidence": "nan",
            },
            "review_report": {"status": "done", "rerender_targets": []},
        },
        {},
    )

    assert captured["style_selection_confidence"] == 0.0



def test_write_pipeline_artifacts_writes_roundtrip_manifest_and_summary_files(monkeypatch, tmp_path):
    monkeypatch.setattr(artifact_paths, "PROJECT_ROOT", tmp_path)

    state = {
        "run_id": "run-roundtrip",
        "status": "done",
        "failure_reason": "",
        "current_stage": "publish",
        "completed_stages": ["plan", "review", "publish"],
        "scope": "run",
    }
    payload = {
        "concept_text": "citypop night drive",
        "style_name": "citypop",
        "style_resolution": {
            "style_name": "citypop",
            "selection_source": "auto",
            "selection_stability": "stable",
            "confidence": 0.93,
        },
        "music_file": "music.mp3",
        "audio_plan": {"genre_description": "citypop"},
        "audio_map": {"sections": [{"name": "verse"}]},
        "shot_plan": [{"shot_id": "S001"}],
        "render_plan": [{"shot_id": "S001", "render_mode": "i2v"}],
        "still_results": [{"shot_id": "S001", "image": "stills/S001.png"}],
        "clip_results": [{"shot_id": "S001", "video": "clips/S001.mp4"}],
        "final_video": "final.mp4",
        "review_inputs": {"music_file": "music.mp3"},
        "review_report": {
            "status": "done",
            "rerender_targets": [],
            "assembly_revision_summary": {
                "present": True,
                "action": "revise_transition_selection",
                "target": "assembly",
                "final_video": "final.mp4",
                "music_file": "music.mp3",
            },
        },
    }

    write_pipeline_artifacts(state, payload, {})

    run_manifest = read_json(tmp_path / "artifacts" / "runs" / "run-roundtrip" / "manifest.json")
    latest_manifest = read_json(tmp_path / "artifacts" / "latest" / "manifest.json")
    latest_success_manifest = read_json(tmp_path / "artifacts" / "latest_success" / "manifest.json")
    run_summary = read_json(tmp_path / "artifacts" / "runs" / "run-roundtrip" / "run_summary.json")
    latest_summary = read_json(tmp_path / "artifacts" / "latest" / "run_summary.json")
    latest_success_summary = read_json(tmp_path / "artifacts" / "latest_success" / "run_summary.json")

    assert run_manifest == latest_manifest == latest_success_manifest
    assert run_summary == latest_summary == latest_success_summary
    assert run_manifest["schema_version"] == "ai_mv_schema_v1"
    assert run_manifest["style_resolution"] == {
        "style_name": "citypop",
        "selection_source": "auto",
        "selection_stability": "stable",
        "confidence": 0.93,
    }
    assert run_summary["schema_version"] == "ai_mv_schema_v1"
    assert run_summary["style_name"] == "citypop"
    assert run_summary["style_selection_source"] == "auto"
    assert run_summary["style_selection_stability"] == "stable"
    assert run_summary["style_selection_confidence"] == 0.93
    assert run_summary["assembly_revision_present"] is True
    assert run_summary["assembly_revision_action"] == "revise_transition_selection"



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
