from pathlib import Path

from ai_mv.analysis.frame_extract import (
    build_ffmpeg_frame_extract_cmd,
    representative_frame_plan,
)


def test_representative_frame_plan_for_clip_uses_first_middle_last_labels(tmp_path):
    out_dir = tmp_path / "frames"

    plan = representative_frame_plan(
        video_path=tmp_path / "clip.mp4",
        output_dir=out_dir,
        kind="clip",
        duration_fn=lambda _path: 12.0,
    )

    assert [row["label"] for row in plan] == ["first", "middle", "last"]
    assert [round(row["timestamp_sec"], 2) for row in plan] == [0.0, 6.0, 11.96]
    assert [row["output_path"].name for row in plan] == ["first.png", "middle.png", "last.png"]


def test_representative_frame_plan_for_final_spreads_sampled_frames(tmp_path):
    out_dir = tmp_path / "frames"

    plan = representative_frame_plan(
        video_path=tmp_path / "final.mp4",
        output_dir=out_dir,
        kind="final",
        sample_count=4,
        duration_fn=lambda _path: 20.0,
    )

    assert [row["label"] for row in plan] == ["final_01", "final_02", "final_03", "final_04"]
    assert [round(row["timestamp_sec"], 1) for row in plan] == [4.0, 8.0, 12.0, 16.0]
    assert [row["output_path"].name for row in plan] == ["final_01.png", "final_02.png", "final_03.png", "final_04.png"]


def test_build_ffmpeg_frame_extract_cmd_seeks_and_writes_single_frame(tmp_path):
    cmd = build_ffmpeg_frame_extract_cmd(
        ffmpeg="ffmpeg",
        video_path=tmp_path / "final.mp4",
        timestamp_sec=12.5,
        output_path=tmp_path / "frame.png",
    )

    assert cmd == [
        "ffmpeg",
        "-y",
        "-ss",
        "12.500",
        "-i",
        str(tmp_path / "final.mp4"),
        "-frames:v",
        "1",
        str(tmp_path / "frame.png"),
    ]
