from pathlib import Path

from ai_mv.core.stages.ffmpeg_muxer import run_ffmpeg_mux


def test_run_ffmpeg_mux_writes_concat_trim_directives(monkeypatch, tmp_path):
    clip = tmp_path / "clip.mp4"
    audio = tmp_path / "song.mp3"
    out = tmp_path / "final.mp4"
    clip.write_text("clip", encoding="utf-8")
    audio.write_text("audio", encoding="utf-8")

    monkeypatch.setattr("ai_mv.core.stages.ffmpeg_muxer.shutil.which", lambda name: "/usr/bin/" + name)

    calls = {}

    def _fake_run(cmd, **kwargs):
        calls["cmd"] = cmd
        concat = out.parent / "concat.txt"
        calls["concat_text"] = concat.read_text(encoding="utf-8")
        out.with_suffix(".tmp.mp4").write_text("video", encoding="utf-8")

        class _Result:
            returncode = 0
            stderr = ""
            stdout = ""

        return _Result()

    monkeypatch.setattr("ai_mv.core.stages.ffmpeg_muxer.subprocess.run", _fake_run)

    ok = run_ffmpeg_mux(
        [{"path": clip, "trim_start_sec": 1.25, "trim_end_sec": 3.5}],
        audio,
        out,
        {"video": {"target": "1920x1080@24"}},
    )

    assert ok is True
    assert "file '" in calls["concat_text"]
    assert "inpoint 1.25" in calls["concat_text"]
    assert "outpoint 3.5" in calls["concat_text"]
