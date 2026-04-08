from pathlib import Path

from ai_mv.core.contracts.stage_io import StageInput
from ai_mv.core.stages.assemble_mv import run_assemble_mv
from ai_mv.core.stages.render_clips import run_render_clips
from ai_mv.core.stages.render_stills import run_render_stills
from ai_mv.core.stages.review_outputs import run_review_outputs


def test_render_stills_calls_qwen_runner(monkeypatch):
    calls = []

    def _fake_run_qwen_still(_config, item):
        calls.append(item)
        return f"D:/renders/{item['shot_id']}.png"

    monkeypatch.setattr("ai_mv.core.stages.render_stills.run_qwen_still", _fake_run_qwen_still)
    stage_input = StageInput(
        run_id="run-1",
        config={"render": {"qwen_negative": "bad anatomy", "qwen_size": "1024x1024"}},
        payload={
            "shot_plan": [{"shot_id": "S001"}],
            "render_plan": [{"shot_id": "S001", "prompt_seed": "city pop girl by the sea"}],
        },
    )

    out = run_render_stills(stage_input)

    assert out.payload["still_results"][0]["image"] == "D:/renders/S001.png"
    assert calls[0]["filename_prefix"] == "stills/S001"
    assert calls[0]["positive_prompt"] == "city pop girl by the sea"


def test_render_clips_routes_i2v(monkeypatch):
    calls = []

    def _fake_run_ltx_i2v(_config, item):
        calls.append(("i2v", item))
        return f"D:/renders/{item['shot_id']}_i2v.mp4"

    monkeypatch.setattr("ai_mv.core.stages.render_clips.run_ltx_i2v", _fake_run_ltx_i2v)
    stage_input = StageInput(
        run_id="run-2",
        config={"render": {"ltx_negative": "bad", "ltx_fps": 24, "ltx_default_shot_sec": 4.0}},
        payload={
            "music_file": "music/song.mp3",
            "shot_plan": [{"shot_id": "S001", "duration_sec": 5.0, "render_mode": "i2v"}],
            "render_plan": [{"shot_id": "S001", "render_mode": "i2v", "prompt_seed": "night drive"}],
            "still_results": [{"shot_id": "S001", "image": "D:/renders/S001.png"}],
        },
    )

    out = run_render_clips(stage_input)

    assert out.payload["clip_results"][0]["video"] == "D:/renders/S001_i2v.mp4"
    assert calls[0][1]["image"] == "D:/renders/S001.png"
    assert calls[0][1]["filename_prefix"] == "clips/S001_i2v"


def test_render_clips_fails_fast_when_i2v_still_is_missing():
    stage_input = StageInput(
        run_id="run-2-missing-still",
        config={"render": {"ltx_negative": "bad", "ltx_fps": 24, "ltx_default_shot_sec": 4.0}},
        payload={
            "music_file": "music/song.mp3",
            "shot_plan": [{"shot_id": "S001", "duration_sec": 5.0, "render_mode": "i2v"}],
            "render_plan": [{"shot_id": "S001", "render_mode": "i2v", "prompt_seed": "night drive"}],
            "still_results": [],
        },
    )

    import pytest

    with pytest.raises(RuntimeError, match="missing source still for shot: S001"):
        run_render_clips(stage_input)


def test_render_clips_fails_fast_when_ia2v_music_file_is_missing():
    stage_input = StageInput(
        run_id="run-2-missing-audio",
        config={"render": {"ltx_negative": "bad", "ltx_fps": 24, "ltx_default_shot_sec": 4.0}},
        payload={
            "music_file": "",
            "shot_plan": [{"shot_id": "S001", "duration_sec": 5.0, "render_mode": "ia2v", "start_sec": 0.0}],
            "render_plan": [{"shot_id": "S001", "render_mode": "ia2v", "prompt_seed": "night drive"}],
            "still_results": [{"shot_id": "S001", "image": "D:/renders/S001.png"}],
        },
    )

    import pytest

    with pytest.raises(RuntimeError, match="missing music file for ia2v shot: S001"):
        run_render_clips(stage_input)


def test_render_clips_routes_flf2v_with_bridge_target(monkeypatch):
    calls = []

    def _fake_run_ltx_flf2v(_config, item):
        calls.append(item)
        return f"D:/renders/{item['shot_id']}_flf2v.mp4"

    def _fake_run_ltx_i2v(_config, item):
        return f"D:/renders/{item['shot_id']}_i2v.mp4"

    monkeypatch.setattr("ai_mv.core.stages.render_clips.run_ltx_flf2v", _fake_run_ltx_flf2v)
    monkeypatch.setattr("ai_mv.core.stages.render_clips.run_ltx_i2v", _fake_run_ltx_i2v)
    stage_input = StageInput(
        run_id="run-2b",
        config={"render": {"ltx_negative": "bad", "ltx_fps": 24, "ltx_default_shot_sec": 4.0}},
        payload={
            "music_file": "music/song.mp3",
            "shot_plan": [
                {"shot_id": "S003", "duration_sec": 4.0, "render_mode": "flf2v", "bridge_to_shot_id": "S004"},
                {"shot_id": "S004", "duration_sec": 4.0, "render_mode": "i2v"},
            ],
            "render_plan": [
                {"shot_id": "S003", "render_mode": "flf2v", "prompt_seed": "bridge move", "still_b": "S004"},
                {"shot_id": "S004", "render_mode": "i2v", "prompt_seed": "chorus hold"},
            ],
            "still_results": [
                {"shot_id": "S003", "image": "D:/renders/S003.png"},
                {"shot_id": "S004", "image": "D:/renders/S004.png"},
            ],
        },
    )

    out = run_render_clips(stage_input)

    assert out.payload["clip_results"][0]["video"] == "D:/renders/S003_flf2v.mp4"
    assert calls[0]["first_image"] == "D:/renders/S003.png"
    assert calls[0]["last_image"] == "D:/renders/S004.png"


def test_assemble_mv_runs_ffmpeg(monkeypatch, tmp_path):
    final_file = tmp_path / "artifacts" / "runs" / "run-3" / "final" / "final_mv.mp4"
    calls = {}

    def _fake_run_file(run_id, name, scope="run"):
        assert run_id == "run-3"
        assert name == "final/final_mv.mp4"
        final_file.parent.mkdir(parents=True, exist_ok=True)
        return final_file

    def _fake_resolve_generated_file(_config, ref, _exts, _label):
        return Path(ref)

    def _fake_run_ffmpeg_mux(clips, audio, out, _config):
        calls["clips"] = clips
        calls["audio"] = audio
        calls["out"] = out
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b"video")
        return True

    monkeypatch.setattr("ai_mv.core.stages.assemble_mv.run_file", _fake_run_file)
    monkeypatch.setattr("ai_mv.core.stages.assemble_mv.resolve_generated_file", _fake_resolve_generated_file)
    monkeypatch.setattr("ai_mv.core.stages.assemble_mv.run_ffmpeg_mux", _fake_run_ffmpeg_mux)
    stage_input = StageInput(
        run_id="run-3",
        config={"video": {"target": "1920x1080@24"}},
        payload={
            "music_file": str(tmp_path / "music.mp3"),
            "clip_results": [{"shot_id": "S001", "video": str(tmp_path / "clip.mp4")}],
        },
    )

    out = run_assemble_mv(stage_input)

    assert out.payload["final_video"] == str(final_file)
    assert calls["out"] == final_file
    assert len(calls["clips"]) == 1


def test_review_outputs_marks_done_when_final_exists():
    final_path = Path("D:/renders/final.mp4")
    existing = {str(final_path), "D:/renders/S001.png", "D:/renders/S001.mp4"}

    def _fake_exists(self):
        return str(self).replace("\\", "/") in {path.replace("\\", "/") for path in existing}

    from pathlib import Path as _Path

    _original_exists = _Path.exists
    _Path.exists = _fake_exists
    try:
        stage_input = StageInput(
            run_id="run-4",
            config={},
            payload={
                "final_video": str(final_path),
                "shot_plan": [{"shot_id": "S001"}],
                "still_results": [{"shot_id": "S001", "image": "D:/renders/S001.png", "status": "done"}],
                "clip_results": [{"shot_id": "S001", "video": "D:/renders/S001.mp4", "status": "done"}],
            },
        )

        out = run_review_outputs(stage_input)

        assert out.payload["review_report"]["status"] == "done"
        assert out.payload["review_report"]["completed_counts"]["clips"] == 1
        assert out.payload["review_report"]["rerender_targets"] == []
    finally:
        _Path.exists = _original_exists


def test_review_outputs_marks_missing_assets_for_rerender():
    stage_input = StageInput(
        run_id="run-5",
        config={},
        payload={
            "final_video": "D:/renders/final.mp4",
            "shot_plan": [{"shot_id": "S001"}, {"shot_id": "S002"}],
            "still_results": [
                {"shot_id": "S001", "image": "D:/renders/S001.png", "status": "done"},
                {"shot_id": "S002", "image": "", "status": "failed"},
            ],
            "clip_results": [
                {"shot_id": "S001", "video": "", "status": "failed"},
                {"shot_id": "S002", "video": "D:/renders/S002.mp4", "status": "done"},
            ],
        },
    )

    out = run_review_outputs(stage_input)

    assert out.payload["review_report"]["status"] == "needs_rerender"
    assert sorted(out.payload["review_report"]["rerender_targets"]) == ["S001", "S002"]
    assert out.payload["review_report"]["blocking_checks"]["all_clips_rendered"] is False


def test_review_outputs_counts_latest_success_per_shot(monkeypatch):
    existing = {"D:/renders/final.mp4", "D:/renders/S001_retry.png", "D:/renders/S001_retry.mp4"}

    def _fake_exists(self):
        return str(self).replace("\\", "/") in {path.replace("\\", "/") for path in existing}

    from pathlib import Path as _Path

    _original_exists = _Path.exists
    _Path.exists = _fake_exists
    try:
        stage_input = StageInput(
            run_id="run-6",
            config={},
            payload={
                "final_video": "D:/renders/final.mp4",
                "shot_plan": [{"shot_id": "S001"}],
                "still_results": [
                    {"shot_id": "S001", "image": "", "status": "failed"},
                    {"shot_id": "S001", "image": "D:/renders/S001_retry.png", "status": "done"},
                ],
                "clip_results": [
                    {"shot_id": "S001", "video": "", "status": "failed"},
                    {"shot_id": "S001", "video": "D:/renders/S001_retry.mp4", "status": "done"},
                ],
            },
        )

        out = run_review_outputs(stage_input)

        assert out.payload["review_report"]["status"] == "done"
        assert out.payload["review_report"]["completed_counts"]["stills"] == 1
        assert out.payload["review_report"]["completed_counts"]["clips"] == 1
        assert out.payload["review_report"]["rerender_targets"] == []
    finally:
        _Path.exists = _original_exists


def test_review_outputs_marks_missing_result_rows_for_rerender():
    stage_input = StageInput(
        run_id="run-7",
        config={"review": {"max_rerender_targets": 3}},
        payload={
            "final_video": "D:/renders/final.mp4",
            "shot_plan": [{"shot_id": "S001"}, {"shot_id": "S002"}],
            "still_results": [{"shot_id": "S001", "image": "D:/renders/S001.png", "status": "done"}],
            "clip_results": [{"shot_id": "S001", "video": "D:/renders/S001.mp4", "status": "done"}],
        },
    )

    out = run_review_outputs(stage_input)

    assert out.payload["review_report"]["status"] == "needs_rerender"
    assert out.payload["review_report"]["rerender_targets"] == ["S001", "S002"]


def test_review_outputs_computes_audio_video_drift(monkeypatch):
    existing = {"D:/renders/final.mp4", "D:/renders/song.mp3", "D:/renders/S001.png", "D:/renders/S001.mp4"}

    def _fake_exists(self):
        return str(self).replace("\\", "/") in {path.replace("\\", "/") for path in existing}

    from pathlib import Path as _Path

    _original_exists = _Path.exists
    _Path.exists = _fake_exists
    monkeypatch.setattr("ai_mv.core.stages.review_outputs.ffprobe_duration", lambda path: 10.0 if str(path).endswith(".mp3") else 10.35)
    try:
        stage_input = StageInput(
            run_id="run-8",
            config={},
            payload={
                "music_file": "D:/renders/song.mp3",
                "final_video": "D:/renders/final.mp4",
                "shot_plan": [{"shot_id": "S001"}],
                "still_results": [{"shot_id": "S001", "image": "D:/renders/S001.png", "status": "done"}],
                "clip_results": [{"shot_id": "S001", "video": "D:/renders/S001.mp4", "status": "done"}],
            },
        )

        out = run_review_outputs(stage_input)

        assert out.payload["review_report"]["audio_video_drift_sec"] == 0.35
    finally:
        _Path.exists = _original_exists
