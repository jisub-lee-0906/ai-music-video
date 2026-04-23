from pathlib import Path

from ai_mv.entrypoints.validate_latest import run_validate_latest



def test_run_validate_latest_builds_artifact_centered_validation_packet(monkeypatch, tmp_path, capsys):
    output_dir = tmp_path / "validation"
    summary_writes = {}
    monkeypatch.setattr(
        "ai_mv.entrypoints.validate_latest.latest_success_file",
        lambda name, scope="run": tmp_path / scope / "latest_success" / name,
    )
    monkeypatch.setattr(
        "ai_mv.entrypoints.validate_latest.read_json",
        lambda path: {
            "run_id": "run-success",
            "assembly": {"final_video": "D:/renders/final.mp4"},
        } if str(path).endswith("manifest.json") else {"run_id": "run-success", "status": "done"},
    )
    monkeypatch.setattr(
        "ai_mv.entrypoints.validate_latest.extract_frames",
        lambda **kwargs: [output_dir / "final-frames" / "frame-01.png", output_dir / "final-frames" / "frame-02.png"],
    )
    monkeypatch.setattr(
        "ai_mv.entrypoints.validate_latest.write_review_packet",
        lambda **kwargs: {
            "manifest_path": output_dir / "review-packet" / "review-packet.json",
            "quality_findings_path": output_dir / "review-packet" / "review-findings.json",
            "reviewer_notes_path": output_dir / "review-packet" / "review-notes.md",
            "contact_sheet_image_path": output_dir / "review-packet" / "contact-sheet.png",
            "contact_sheet_manifest_path": output_dir / "review-packet" / "contact-sheet.json",
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
    assert str(summary_writes["path"]).endswith("validation-summary.json")
    assert summary_writes["data"] == {
        "run_id": "run-success",
        "scope": "run",
        "manifest_path": str(tmp_path / "run" / "latest_success" / "manifest.json"),
        "run_summary_path": str(tmp_path / "run" / "latest_success" / "run_summary.json"),
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
    }
