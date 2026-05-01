from pathlib import Path

from ai_mv.entrypoints.validate_latest import run_validate_latest



def test_run_validate_latest_builds_artifact_centered_validation_packet(monkeypatch, tmp_path, capsys):
    output_dir = tmp_path / "validation"
    summary_writes = {}
    packet_calls = {}
    monkeypatch.setattr(
        "ai_mv.entrypoints.validate_latest.latest_success_file",
        lambda name, scope="run": tmp_path / scope / "latest_success" / name,
    )
    monkeypatch.setattr(
        "ai_mv.entrypoints.validate_latest.read_json",
        lambda path: {
            "run_id": "run-success",
            "assembly": {"final_video": "D:/renders/final.mp4"},
        } if str(path).endswith("manifest.json") else {
            "run_id": "run-success",
            "status": "done",
            "overall_status": "review_required",
            "publishability_tier": "needs_revision",
            "recommended_next_action": "revise_transition_selection",
            "review_severity": {
                "drift": "medium",
                "coverage": "low",
                "visual_quality": "high",
                "assembly_quality": "high",
            },
            "review_severity_drift": "medium",
            "review_severity_coverage": "low",
            "review_severity_visual_quality": "high",
            "review_severity_assembly_quality": "high",
            "review_signal_buckets": {
                "measurable_deterministic": {"passed": True, "failed_checks": []},
                "heuristic_proxy": {
                    "passed": False,
                    "failed_checks": ["safe_editing_within_threshold", "camera_restraint"],
                },
                "model_judged": {"passed": False, "failed_checks": ["mood_consistency"]},
            },
            "review_signal_bucket_failed_checks": [
                "safe_editing_within_threshold",
                "camera_restraint",
                "mood_consistency",
            ],
        },
    )
    monkeypatch.setattr(
        "ai_mv.entrypoints.validate_latest.extract_frames",
        lambda **kwargs: [output_dir / "final-frames" / "frame-01.png", output_dir / "final-frames" / "frame-02.png"],
    )
    def _fake_write_review_packet(**kwargs):
        packet_calls.update(kwargs)
        return {
            "manifest_path": output_dir / "review-packet" / "review-packet.json",
            "quality_findings_path": output_dir / "review-packet" / "review-findings.json",
            "reviewer_notes_path": output_dir / "review-packet" / "review-notes.md",
            "contact_sheet_image_path": output_dir / "review-packet" / "contact-sheet.png",
            "contact_sheet_manifest_path": output_dir / "review-packet" / "contact-sheet.json",
        }

    monkeypatch.setattr(
        "ai_mv.entrypoints.validate_latest.write_review_packet",
        _fake_write_review_packet,
    )
    monkeypatch.setattr(
        "ai_mv.entrypoints.validate_latest.write_audio_review_packet",
        lambda **kwargs: {
            "manifest_path": output_dir / "audio-review" / "audio-review-packet.json",
            "rubric_path": output_dir / "audio-review" / "audio-review-rubric.json",
            "reviewer_notes_path": output_dir / "audio-review" / "audio-review-notes.md",
        },
    )
    def _fake_write_json(path, data):
        summary_writes["path"] = path
        summary_writes["data"] = data

    monkeypatch.setattr(
        "ai_mv.entrypoints.validate_latest.write_json",
        _fake_write_json,
    )

    rc = run_validate_latest(output_dir=str(output_dir), sample_count=8, shot_ids=["S001", "S002"])
    out = capsys.readouterr().out

    assert rc == 0
    assert "run_id=run-success" in out
    assert str(output_dir / "final-frames") in out
    assert str(output_dir / "review-packet" / "review-packet.json") in out
    assert str(output_dir / "audio-review" / "audio-review-packet.json") in out
    assert str(summary_writes["path"]).endswith("validation-summary.json")
    assert packet_calls["shot_ids"] == ["S001", "S002"]
    assert summary_writes["data"] == {
        "run_id": "run-success",
        "scope": "run",
        "manifest_path": str(tmp_path / "run" / "latest_success" / "manifest.json"),
        "run_summary_path": str(tmp_path / "run" / "latest_success" / "run_summary.json"),
        "overall_status": "review_required",
        "publishability_tier": "needs_revision",
        "recommended_next_action": "revise_transition_selection",
        "review_severity": {
            "drift": "medium",
            "coverage": "low",
            "visual_quality": "high",
            "assembly_quality": "high",
        },
        "review_severity_drift": "medium",
        "review_severity_coverage": "low",
        "review_severity_visual_quality": "high",
        "review_severity_assembly_quality": "high",
        "review_signal_buckets": {
            "measurable_deterministic": {"passed": True, "failed_checks": []},
            "heuristic_proxy": {
                "passed": False,
                "failed_checks": ["safe_editing_within_threshold", "camera_restraint"],
            },
            "model_judged": {"passed": False, "failed_checks": ["mood_consistency"]},
        },
        "review_signal_bucket_failed_checks": [
            "safe_editing_within_threshold",
            "camera_restraint",
            "mood_consistency",
        ],
        "final_video": "D:/renders/final.mp4",
        "frames_dir": str(output_dir / "final-frames"),
        "frames_written": [
            str(output_dir / "final-frames" / "frame-01.png"),
            str(output_dir / "final-frames" / "frame-02.png"),
        ],
        "review_packet_manifest": str(output_dir / "review-packet" / "review-packet.json"),
        "review_findings": str(output_dir / "review-packet" / "review-findings.json"),
        "review_notes": str(output_dir / "review-packet" / "review-notes.md"),
        "contact_sheet_image": str(output_dir / "review-packet" / "contact-sheet.png"),
        "contact_sheet_manifest": str(output_dir / "review-packet" / "contact-sheet.json"),
        "audio_review_packet_manifest": str(output_dir / "audio-review" / "audio-review-packet.json"),
        "audio_review_rubric": str(output_dir / "audio-review" / "audio-review-rubric.json"),
        "audio_review_notes": str(output_dir / "audio-review" / "audio-review-notes.md"),
    }


def test_run_validate_latest_uses_manifest_render_plan_shot_ids_for_review_packet(monkeypatch, tmp_path):
    output_dir = tmp_path / "validation"
    packet_calls = {}
    monkeypatch.setattr(
        "ai_mv.entrypoints.validate_latest.latest_success_file",
        lambda name, scope="run": tmp_path / scope / "latest_success" / name,
    )
    monkeypatch.setattr(
        "ai_mv.entrypoints.validate_latest.read_json",
        lambda path: {
            "run_id": "run-success",
            "assembly": {"final_video": "D:/renders/final.mp4"},
            "plan": {
                "render_plan": [
                    {"shot_id": "S001"},
                    {
                        "shot_id": "S002",
                        "production_policy": {
                            "candidate_role": "high_risk_interaction_payoff",
                            "ia2v_risk_class": "red",
                            "anchor_reference_arm": "D_FULLBODY_UPPER",
                            "recommended_duration_sec": {"min": 0.3, "max": 0.7},
                        },
                    },
                    {"shot_id": "S001"},
                    {"shot_id": ""},
                ]
            },
            "song": {"master_audio": ""},
        } if str(path).endswith("manifest.json") else {
            "run_id": "run-success",
            "status": "done",
        },
    )
    monkeypatch.setattr(
        "ai_mv.entrypoints.validate_latest.extract_frames",
        lambda **kwargs: [],
    )

    def _fake_write_review_packet(**kwargs):
        packet_calls.update(kwargs)
        return {
            "manifest_path": output_dir / "review-packet" / "review-packet.json",
            "quality_findings_path": output_dir / "review-packet" / "review-findings.json",
            "reviewer_notes_path": output_dir / "review-packet" / "review-notes.md",
            "contact_sheet_image_path": output_dir / "review-packet" / "contact-sheet.png",
            "contact_sheet_manifest_path": output_dir / "review-packet" / "contact-sheet.json",
        }

    monkeypatch.setattr(
        "ai_mv.entrypoints.validate_latest.write_review_packet",
        _fake_write_review_packet,
    )
    monkeypatch.setattr(
        "ai_mv.entrypoints.validate_latest.write_json",
        lambda path, data: None,
    )

    rc = run_validate_latest(output_dir=str(output_dir), sample_count=8)

    assert rc == 0
    assert packet_calls["shot_ids"] == ["S001", "S002"]
    assert packet_calls["escalation_context"]["production_policy_by_shot"] == {
        "S002": {
            "candidate_role": "high_risk_interaction_payoff",
            "ia2v_risk_class": "red",
            "anchor_reference_arm": "D_FULLBODY_UPPER",
            "recommended_duration_sec": {"min": 0.3, "max": 0.7},
        }
    }
