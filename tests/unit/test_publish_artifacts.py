from ai_mv.core.artifacts import paths as artifact_paths
from ai_mv.core.artifacts.publish import write_pipeline_artifacts
from ai_mv.core.artifacts.manifest import write_manifest
from ai_mv.utils.json_utils import read_json


def test_write_manifest_emits_blueprint_aligned_public_output_contract(monkeypatch):
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
            "style_lane": "citypop",
            "style_resolution": {"style_lane": "citypop", "selection_source": "auto"},
            "section_plan": [{"section_id": "SEC_001", "section_type": "verse"}],
            "material_plan": [{"material_id": "MAT_001", "section_id": "SEC_001"}],
            "shot_plan": [{"shot_id": "S001"}],
            "render_plan": [{"shot_id": "S001", "render_mode": "i2v"}],
            "still_results": [{"shot_id": "S001", "image": "stills/S001.png"}],
            "clip_results": [{"shot_id": "S001", "video": "clips/S001.mp4"}],
            "review_report": {"status": "done", "rerender_targets": []},
            "final_video": "final.mp4",
            "assembly_plan": {"section_edits": [{"section_id": "SEC_001"}]},
            "review_inputs": {"music_file": "music.mp3"},
            "rerender_escalation": {"artifacts": {"review_packet_manifest": "review/review-packet.json"}},
        },
    )

    manifest = captured[0][1]
    assert manifest["schema_version"] == "ai_mv_schema_v2"
    assert manifest["input"] == {"concept_text": "citypop night drive"}
    assert manifest["song"] == {
        "master_audio": "music.mp3",
        "section_map": {"sections": [{"name": "verse"}]},
        "audio_plan": {"genre_description": "citypop"},
    }
    assert manifest["plan"] == {
        "style_lane": "citypop",
        "style_resolution": {"style_lane": "citypop", "selection_source": "auto"},
        "section_plan": [{"section_id": "SEC_001", "section_type": "verse"}],
        "material_plan": [{"material_id": "MAT_001", "section_id": "SEC_001"}],
        "render_plan": [{"shot_id": "S001", "render_mode": "i2v"}],
    }
    assert manifest["stills"] == {"material_results": [{"shot_id": "S001", "image": "stills/S001.png"}]}
    assert manifest["clips"] == {"clip_results": [{"shot_id": "S001", "video": "clips/S001.mp4"}]}
    assert manifest["assembly"] == {
        "final_video": "final.mp4",
        "assembly_plan": {"section_edits": [{"section_id": "SEC_001"}]},
        "review_inputs": {"music_file": "music.mp3"},
    }
    assert manifest["review"] == {
        "review_report": {"status": "done", "rerender_targets": []},
        "review_packet_manifest": "review/review-packet.json",
    }
    assert manifest["artifacts"] == {"scope": "run"}
    assert "concept_text" not in manifest
    assert "style_lane" not in manifest
    assert "style_bible" not in manifest
    assert "planner_prompts" not in manifest
    assert "workflow_inputs" not in manifest
    assert "workflow_inputs_preview" not in manifest
    assert "render_inputs" not in manifest
    assert "audio_plan" not in manifest
    assert "audio_map" not in manifest
    assert "style_resolution" not in manifest
    assert "shot_plan" not in manifest
    assert "section_plan" not in manifest
    assert "material_plan" not in manifest
    assert "render_plan" not in manifest
    assert "still_results" not in manifest
    assert "clip_results" not in manifest
    assert "assembly_plan" not in manifest
    assert "review_report" not in manifest
    assert "final_video" not in manifest
    assert "music_file" not in manifest
    assert "legacy" not in manifest



def test_write_manifest_is_empty_safe_for_blueprint_public_output_sections(monkeypatch):
    captured = []

    monkeypatch.setattr("ai_mv.core.artifacts.manifest.write_json", lambda path, payload: captured.append((str(path), payload)))
    monkeypatch.setattr("ai_mv.core.artifacts.manifest.run_file", lambda run_id, name, scope: f"/tmp/{run_id}/{scope}/{name}")
    monkeypatch.setattr("ai_mv.core.artifacts.manifest.latest_file", lambda name, scope: f"/tmp/latest/{scope}/{name}")
    monkeypatch.setattr("ai_mv.core.artifacts.manifest.latest_success_file", lambda name, scope: f"/tmp/latest-success/{scope}/{name}")

    write_manifest(
        {"run_id": "run-201", "status": "done", "failure_reason": "", "scope": "run"},
        {
            "concept_text": "dreamy dusk drive",
            "style_lane": "dream_pop",
        },
    )

    manifest = captured[0][1]
    assert manifest["schema_version"] == "ai_mv_schema_v2"
    assert manifest["song"] == {"master_audio": "", "section_map": {}, "audio_plan": {}}
    assert manifest["plan"] == {
        "style_lane": "dream_pop",
        "style_resolution": {"style_lane": "dream_pop"},
        "section_plan": [],
        "material_plan": [],
        "render_plan": [],
    }
    assert manifest["stills"] == {"material_results": []}
    assert manifest["clips"] == {"clip_results": []}
    assert manifest["assembly"] == {"final_video": "", "assembly_plan": {}, "review_inputs": {}}
    assert manifest["review"] == {"review_report": {}, "review_packet_manifest": ""}
    assert manifest["artifacts"] == {"scope": "run"}



def test_write_manifest_backfills_section_plan_from_audio_map_when_public_section_plan_is_absent(monkeypatch):
    captured = []

    monkeypatch.setattr("ai_mv.core.artifacts.manifest.write_json", lambda path, payload: captured.append((str(path), payload)))
    monkeypatch.setattr("ai_mv.core.artifacts.manifest.run_file", lambda run_id, name, scope: f"/tmp/{run_id}/{scope}/{name}")
    monkeypatch.setattr("ai_mv.core.artifacts.manifest.latest_file", lambda name, scope: f"/tmp/latest/{scope}/{name}")
    monkeypatch.setattr("ai_mv.core.artifacts.manifest.latest_success_file", lambda name, scope: f"/tmp/latest-success/{scope}/{name}")

    write_manifest(
        {"run_id": "run-201b", "status": "done", "failure_reason": "", "scope": "run"},
        {
            "concept_text": "dreamy dusk drive",
            "style_lane": "dream_pop",
            "audio_map": {
                "duration_sec": 12.0,
                "sections": [
                    {"name": "intro", "start_sec": 0.0, "end_sec": 4.0},
                    {"name": "chorus", "start_sec": 4.0, "end_sec": 12.0},
                ],
            },
        },
    )

    manifest = captured[0][1]
    assert [row["section_type"] for row in manifest["plan"]["section_plan"]] == ["intro", "chorus"]
    assert manifest["plan"]["section_plan"][0]["start_sec"] == 0.0
    assert manifest["plan"]["section_plan"][1]["end_sec"] == 12.0



def test_write_manifest_does_not_synthesize_section_plan_from_audio_duration_alone(monkeypatch):
    captured = []

    monkeypatch.setattr("ai_mv.core.artifacts.manifest.write_json", lambda path, payload: captured.append((str(path), payload)))
    monkeypatch.setattr("ai_mv.core.artifacts.manifest.run_file", lambda run_id, name, scope: f"/tmp/{run_id}/{scope}/{name}")
    monkeypatch.setattr("ai_mv.core.artifacts.manifest.latest_file", lambda name, scope: f"/tmp/latest/{scope}/{name}")
    monkeypatch.setattr("ai_mv.core.artifacts.manifest.latest_success_file", lambda name, scope: f"/tmp/latest-success/{scope}/{name}")

    write_manifest(
        {"run_id": "run-201c", "status": "done", "failure_reason": "", "scope": "run"},
        {
            "concept_text": "dreamy dusk drive",
            "style_lane": "dream_pop",
            "audio_map": {"duration_sec": 16.0},
        },
    )

    manifest = captured[0][1]
    assert manifest["song"]["section_map"] == {"duration_sec": 16.0}
    assert manifest["plan"]["section_plan"] == []



def test_write_manifest_does_not_synthesize_section_plan_from_malformed_section_rows(monkeypatch):
    captured = []

    monkeypatch.setattr("ai_mv.core.artifacts.manifest.write_json", lambda path, payload: captured.append((str(path), payload)))
    monkeypatch.setattr("ai_mv.core.artifacts.manifest.run_file", lambda run_id, name, scope: f"/tmp/{run_id}/{scope}/{name}")
    monkeypatch.setattr("ai_mv.core.artifacts.manifest.latest_file", lambda name, scope: f"/tmp/latest/{scope}/{name}")
    monkeypatch.setattr("ai_mv.core.artifacts.manifest.latest_success_file", lambda name, scope: f"/tmp/latest-success/{scope}/{name}")

    write_manifest(
        {"run_id": "run-201d", "status": "done", "failure_reason": "", "scope": "run"},
        {
            "concept_text": "dreamy dusk drive",
            "style_lane": "dream_pop",
            "audio_map": {
                "duration_sec": 16.0,
                "sections": [
                    {"name": "verse"},
                    {"name": "chorus", "start_sec": 4.0, "end_sec": 4.0},
                ],
            },
        },
    )

    manifest = captured[0][1]
    assert manifest["plan"]["section_plan"] == []



def test_write_pipeline_artifacts_includes_schema_and_assembly_revision_in_run_summary(monkeypatch):
    captured = {}
    monkeypatch.setattr("ai_mv.core.artifacts.publish.write_manifest", lambda state, payload: None)
    monkeypatch.setattr("ai_mv.core.artifacts.publish.write_run_summary", lambda state, summary: captured.update(summary))

    write_pipeline_artifacts(
        {"run_id": "run-122", "status": "done", "current_stage": "publish", "completed_stages": ["plan", "review", "publish"]},
        {
            "concept_text": "citypop night drive",
            "style_lane": "citypop",
            "style_resolution": {
                "style_lane": "citypop",
                "selection_source": "auto",
                "selection_stability": "stable",
                "confidence": 0.93,
            },
            "final_video": "final.mp4",
            "music_file": "music.mp3",
            "review_report": {
                "status": "done",
                "rerender_targets": [],
                "overall_status": "pass",
                "publishability_tier": "publishable",
                "recommended_next_action": "publish",
                "scores": {
                    "overall": 100.0,
                    "technical_completion": 100.0,
                    "material_quality": 100.0,
                    "final_mv_quality": 84.0,
                },
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

    assert captured["schema_version"] == "ai_mv_schema_v2"
    assert captured["style_lane"] == "citypop"
    assert captured["style_selection_source"] == "auto"
    assert captured["style_selection_stability"] == "stable"
    assert captured["style_selection_confidence"] == 0.93
    assert captured["assembly_revision_present"] is True
    assert captured["assembly_revision_action"] == "revise_transition_selection"
    assert captured["assembly_revision_target"] == "assembly"
    assert captured["assembly_revision_final_video"] == "final.mp4"
    assert captured["assembly_revision_music_file"] == "music.mp3"
    assert captured["overall_status"] == "pass"
    assert captured["publishability_tier"] == "publishable"
    assert captured["recommended_next_action"] == "publish"
    assert captured["overall_score"] == 100.0
    assert captured["technical_completion_score"] == 100.0
    assert captured["material_quality_score"] == 100.0
    assert captured["final_mv_quality_score"] == 84.0



def test_write_pipeline_artifacts_sanitizes_invalid_style_selection_confidence(monkeypatch):
    captured = {}
    monkeypatch.setattr("ai_mv.core.artifacts.publish.write_manifest", lambda state, payload: None)
    monkeypatch.setattr("ai_mv.core.artifacts.publish.write_run_summary", lambda state, summary: captured.update(summary))

    write_pipeline_artifacts(
        {"run_id": "run-122b", "status": "done", "current_stage": "publish", "completed_stages": ["plan", "publish"]},
        {
            "concept_text": "citypop night drive",
            "style_lane": "citypop",
            "style_resolution": {
                "style_lane": "citypop",
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
        "style_lane": "citypop",
        "style_resolution": {
            "style_lane": "citypop",
            "selection_source": "auto",
            "selection_stability": "stable",
            "confidence": 0.93,
        },
        "music_file": "music.mp3",
        "audio_plan": {"genre_description": "citypop"},
        "audio_map": {"sections": [{"name": "verse"}]},
        "section_plan": [{"section_id": "SEC_001", "section_type": "verse"}],
        "material_plan": [{"material_id": "MAT_001", "section_id": "SEC_001"}],
        "shot_plan": [{"shot_id": "S001"}],
        "render_plan": [{"shot_id": "S001", "render_mode": "i2v"}],
        "still_results": [{"shot_id": "S001", "image": "stills/S001.png"}],
        "clip_results": [{"shot_id": "S001", "video": "clips/S001.mp4"}],
        "final_video": "final.mp4",
        "assembly_plan": {"section_edits": [{"section_id": "SEC_001"}]},
        "review_inputs": {"music_file": "music.mp3"},
        "review_report": {
            "status": "done",
            "rerender_targets": [],
            "overall_status": "pass",
            "publishability_tier": "publishable",
            "recommended_next_action": "publish",
            "scores": {
                "overall": 100.0,
                "technical_completion": 100.0,
                "material_quality": 100.0,
                "final_mv_quality": 84.0,
            },
            "assembly_revision_summary": {
                "present": True,
                "action": "revise_transition_selection",
                "target": "assembly",
                "final_video": "final.mp4",
                "music_file": "music.mp3",
            },
        },
        "rerender_escalation": {"artifacts": {"review_packet_manifest": "review/review-packet.json"}},
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
    assert run_manifest["schema_version"] == "ai_mv_schema_v2"
    assert run_manifest["song"] == {
        "master_audio": "music.mp3",
        "section_map": {"sections": [{"name": "verse"}]},
        "audio_plan": {"genre_description": "citypop"},
    }
    assert run_manifest["plan"] == {
        "style_lane": "citypop",
        "style_resolution": {
            "style_lane": "citypop",
            "selection_source": "auto",
            "selection_stability": "stable",
            "confidence": 0.93,
        },
        "section_plan": [{"section_id": "SEC_001", "section_type": "verse"}],
        "material_plan": [{"material_id": "MAT_001", "section_id": "SEC_001"}],
        "render_plan": [{"shot_id": "S001", "render_mode": "i2v"}],
    }
    assert run_manifest["stills"] == {"material_results": [{"shot_id": "S001", "image": "stills/S001.png"}]}
    assert run_manifest["clips"] == {"clip_results": [{"shot_id": "S001", "video": "clips/S001.mp4"}]}
    assert run_manifest["assembly"] == {
        "final_video": "final.mp4",
        "assembly_plan": {"section_edits": [{"section_id": "SEC_001"}]},
        "review_inputs": {"music_file": "music.mp3"},
    }
    assert run_manifest["review"] == {
        "review_report": {
            "status": "done",
            "rerender_targets": [],
            "overall_status": "pass",
            "publishability_tier": "publishable",
            "recommended_next_action": "publish",
            "scores": {
                "overall": 100.0,
                "technical_completion": 100.0,
                "material_quality": 100.0,
                "final_mv_quality": 84.0,
            },
            "assembly_revision_summary": {
                "present": True,
                "action": "revise_transition_selection",
                "target": "assembly",
                "final_video": "final.mp4",
                "music_file": "music.mp3",
            },
        },
        "review_packet_manifest": "review/review-packet.json",
    }
    assert run_summary["schema_version"] == "ai_mv_schema_v2"
    assert run_summary["style_lane"] == "citypop"
    assert run_summary["style_selection_source"] == "auto"
    assert run_summary["style_selection_stability"] == "stable"
    assert run_summary["style_selection_confidence"] == 0.93
    assert run_summary["assembly_revision_present"] is True
    assert run_summary["assembly_revision_action"] == "revise_transition_selection"
    assert run_summary["overall_status"] == "pass"
    assert run_summary["publishability_tier"] == "publishable"
    assert run_summary["recommended_next_action"] == "publish"
    assert run_summary["overall_score"] == 100.0
    assert run_summary["technical_completion_score"] == 100.0
    assert run_summary["material_quality_score"] == 100.0
    assert run_summary["final_mv_quality_score"] == 84.0



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
