import json

from ai_mv.analysis.review_packet import build_review_packet_manifest


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
