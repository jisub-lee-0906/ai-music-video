import json

from ai_mv.analysis.review_packet import build_review_packet_manifest, write_review_packet


def test_build_review_packet_manifest_for_final_includes_expected_paths(tmp_path):
    manifest = build_review_packet_manifest(
        video_path=tmp_path / "final.mp4",
        output_dir=tmp_path / "review-packet",
        kind="final",
        shot_ids=["S001", "S002"],
        sample_count=4,
        duration_fn=lambda _path: 20.0,
    )

    assert manifest["video_path"] == str(tmp_path / "final.mp4")
    assert manifest["kind"] == "final"
    assert manifest["sample_count"] == 4
    assert manifest["shot_ids"] == ["S001", "S002"]
    assert manifest["frame_paths"] == [
        str(tmp_path / "review-packet" / "frames" / "final_01.png"),
        str(tmp_path / "review-packet" / "frames" / "final_02.png"),
        str(tmp_path / "review-packet" / "frames" / "final_03.png"),
        str(tmp_path / "review-packet" / "frames" / "final_04.png"),
    ]
    assert manifest["quality_findings_path"] == str(tmp_path / "review-packet" / "review-findings.json")
    assert manifest["reviewer_notes_path"] == str(tmp_path / "review-packet" / "review-notes.md")
    assert manifest["contact_sheet_image_path"] == str(tmp_path / "review-packet" / "contact-sheet.png")
    assert manifest["contact_sheet_manifest_path"] == str(tmp_path / "review-packet" / "contact-sheet.json")
    assert manifest["frame_count"] == 4
    assert manifest["reviewer_summary"] == "Review packet for 2 shots with 4 extracted frames"


def test_build_review_packet_manifest_is_json_serializable(tmp_path):
    manifest = build_review_packet_manifest(
        video_path=tmp_path / "clip.mp4",
        output_dir=tmp_path / "packet",
        kind="clip",
        shot_ids=["S006"],
        sample_count=6,
        duration_fn=lambda _path: 12.0,
    )

    data = json.loads(json.dumps(manifest))
    assert data["kind"] == "clip"
    assert data["frame_paths"] == [
        str(tmp_path / "packet" / "frames" / "first.png"),
        str(tmp_path / "packet" / "frames" / "middle.png"),
        str(tmp_path / "packet" / "frames" / "last.png"),
    ]
    assert data["contact_sheet_image_path"] == str(tmp_path / "packet" / "contact-sheet.png")


def test_write_review_packet_returns_contact_sheet_image_path(tmp_path):
    written = write_review_packet(
        video_path=tmp_path / "clip.mp4",
        output_dir=tmp_path / "packet",
        kind="clip",
        shot_ids=["S006"],
        sample_count=6,
        duration_fn=lambda _path: 12.0,
    )

    assert written["contact_sheet_image_path"] == tmp_path / "packet" / "contact-sheet.png"
    assert written["contact_sheet_manifest_path"] == tmp_path / "packet" / "contact-sheet.json"
