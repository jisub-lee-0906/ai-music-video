from pathlib import Path

from ai_mv.analysis.audio_review_packet import build_audio_review_packet_manifest, write_audio_review_packet


def test_build_audio_review_packet_manifest_prioritizes_core_listening_segments():
    manifest = build_audio_review_packet_manifest(
        music_path="/tmp/music.mp3",
        output_dir="/tmp/audio-review",
        audio_plan={"genre_description": "bright idol pop", "language": "ko", "hook_brief": "crowd-ready hook"},
        sections=[
            {"name": "intro", "start_sec": 0.0, "end_sec": 4.0},
            {"name": "verse", "start_sec": 4.0, "end_sec": 12.0},
            {"name": "chorus", "start_sec": 12.0, "end_sec": 24.0},
            {"name": "bridge", "start_sec": 24.0, "end_sec": 32.0},
            {"name": "chorus", "start_sec": 32.0, "end_sec": 44.0},
            {"name": "outro", "start_sec": 44.0, "end_sec": 48.0},
        ],
        duration_sec=48.0,
    )

    assert manifest["music_path"] == "/tmp/music.mp3"
    assert manifest["duration_sec"] == 48.0
    assert manifest["section_count"] == 6
    assert manifest["reviewer_summary"] == "Audio review packet with 5 listening segments"
    assert [segment["segment_id"] for segment in manifest["segments"]] == [
        "opener_window",
        "first_chorus",
        "bridge_window",
        "final_chorus",
        "outro_tail",
    ]
    assert manifest["segments"][1]["section_name"] == "chorus"
    assert manifest["segments"][1]["review_axes"] == ["hook_memorability", "genre_fit", "mv_cue_strength"]
    assert manifest["rubric_path"] == "/tmp/audio-review/audio-review-rubric.json"
    assert manifest["reviewer_notes_path"] == "/tmp/audio-review/audio-review-notes.md"


def test_build_audio_review_packet_manifest_does_not_misclassify_pre_chorus_as_chorus():
    manifest = build_audio_review_packet_manifest(
        music_path="/tmp/music.mp3",
        output_dir="/tmp/audio-review",
        audio_plan={"genre_description": "citypop", "language": "ko"},
        sections=[
            {"name": "intro", "start_sec": 0.0, "end_sec": 2.0},
            {"name": "pre_chorus", "start_sec": 2.0, "end_sec": 4.0},
            {"name": "chorus", "start_sec": 4.0, "end_sec": 8.0},
            {"name": "outro", "start_sec": 8.0, "end_sec": 10.0},
        ],
        duration_sec=10.0,
    )

    first_chorus = next(segment for segment in manifest["segments"] if segment["segment_id"] == "first_chorus")
    assert first_chorus["start_sec"] == 4.0
    assert first_chorus["section_name"] == "chorus"


def test_write_audio_review_packet_emits_manifest_rubric_and_notes(tmp_path):
    written = write_audio_review_packet(
        music_path=tmp_path / "music.mp3",
        output_dir=tmp_path / "audio-review",
        audio_plan={"genre_description": "citypop", "language": "ja"},
        sections=[
            {"name": "intro", "start_sec": 0.0, "end_sec": 5.0},
            {"name": "chorus", "start_sec": 5.0, "end_sec": 17.0},
        ],
        duration_sec=17.0,
    )

    assert written["manifest_path"].exists()
    assert written["rubric_path"].exists()
    assert written["reviewer_notes_path"].exists()
    assert "hook_memorability" in written["rubric_path"].read_text(encoding="utf-8")
    notes = written["reviewer_notes_path"].read_text(encoding="utf-8")
    assert "# Audio Review Notes" in notes
    assert "first_chorus" in notes
