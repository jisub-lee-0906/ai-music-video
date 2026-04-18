from pathlib import Path

from ai_mv.core.contracts.stage_io import StageInput, StageOutput
from ai_mv.core.stages.assemble_mv import run_assemble_mv
from ai_mv.core.stages.execute_rerender import run_execute_rerender
from ai_mv.core.stages.prepare_rerender import run_prepare_rerender
from ai_mv.core.stages.repair_rerender_prompts import run_repair_rerender_prompts
from ai_mv.core.stages.render_clips import _clip_prompt_text, run_render_clips
from ai_mv.core.stages.render_stills import _still_prompt_text, run_render_stills
from ai_mv.core.stages.rerender_escalation import run_rerender_escalation
from ai_mv.core.stages.rerender_loop import run_rerender_loop
from ai_mv.core.stages.rerender_review import run_rerender_review
from ai_mv.core.stages.review_outputs import run_review_outputs


def test_render_stills_uses_generic_fallback_prompt_text_when_empty():
    prompt = _still_prompt_text({})

    assert prompt
    assert "city pop" not in prompt.lower()


def test_render_clips_uses_generic_fallback_prompt_text_when_empty():
    prompt = _clip_prompt_text({})

    assert prompt
    assert "city pop" not in prompt.lower()


def test_render_stills_prefers_workflow_specific_still_prompt_text():
    prompt = _still_prompt_text({"still_prompt_text": "single-subject keyframe, motion-safe keyframe"})

    assert prompt == "single-subject keyframe, motion-safe keyframe"


def test_render_clips_prefers_workflow_specific_clip_prompt_seed():
    prompt = _clip_prompt_text({"clip_prompt_seed": "camera drift forward, stable motion"})

    assert prompt == "camera drift forward, stable motion"


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
    assert "city pop girl by the sea" in calls[0]["positive_prompt"]
    assert "single cinematic keyframe" in calls[0]["positive_prompt"]
    assert "one uninterrupted composition" in calls[0]["positive_prompt"]


def test_render_stills_adds_single_keyframe_constraints_to_prompt(monkeypatch):
    calls = []

    def _fake_run_qwen_still(_config, item):
        calls.append(item)
        return f"D:/renders/{item['shot_id']}.png"

    monkeypatch.setattr("ai_mv.core.stages.render_stills.run_qwen_still", _fake_run_qwen_still)
    stage_input = StageInput(
        run_id="run-1b",
        config={"render": {"qwen_negative": "bad anatomy", "qwen_size": "1024x1024"}},
        payload={
            "shot_plan": [{"shot_id": "S009"}],
            "render_plan": [{"shot_id": "S009", "prompt_polish": "night station portrait, reflective glass, film grain"}],
        },
    )

    run_render_stills(stage_input)

    prompt = calls[0]["positive_prompt"]
    assert "night station portrait, reflective glass, film grain" in prompt
    assert "anime film still" in prompt
    assert "single cinematic keyframe" in prompt
    assert "no inset portrait" in prompt


def test_render_stills_strips_panel_prone_graphic_prompt_tokens(monkeypatch):
    calls = []

    def _fake_run_qwen_still(_config, item):
        calls.append(item)
        return f"D:/renders/{item['shot_id']}.png"

    monkeypatch.setattr("ai_mv.core.stages.render_stills.run_qwen_still", _fake_run_qwen_still)
    stage_input = StageInput(
        run_id="run-1c",
        config={"render": {"qwen_negative": "bad anatomy", "qwen_size": "1280x720"}},
        payload={
            "shot_plan": [{"shot_id": "S010"}],
            "render_plan": [
                {
                    "shot_id": "S010",
                    "prompt_polish": "night station portrait, bold graphic composition, graphic reflective close-up styling, reflective glass, film grain",
                }
            ],
        },
    )

    run_render_stills(stage_input)

    prompt = calls[0]["positive_prompt"]
    assert "night station portrait" in prompt
    assert "reflective glass" in prompt
    assert "film grain" in prompt
    assert "bold graphic composition" not in prompt
    assert "graphic reflective close-up styling" not in prompt
    assert "full-bleed frame" in prompt


def test_render_stills_strips_storyboard_like_meta_prompt_tokens(monkeypatch):
    calls = []

    def _fake_run_qwen_still(_config, item):
        calls.append(item)
        return f"D:/renders/{item['shot_id']}.png"

    monkeypatch.setattr("ai_mv.core.stages.render_stills.run_qwen_still", _fake_run_qwen_still)
    stage_input = StageInput(
        run_id="run-1d",
        config={"render": {"qwen_negative": "bad anatomy", "qwen_size": "1280x720"}},
        payload={
            "shot_plan": [{"shot_id": "S011"}],
            "render_plan": [
                {
                    "shot_id": "S011",
                    "prompt_polish": "Japanese 80s city pop music video, progression: opening pass through the night, scene event: late-night city movement, a close-up of a singer in reflected night light, film grain",
                }
            ],
        },
    )

    run_render_stills(stage_input)

    prompt = calls[0]["positive_prompt"]
    assert "a close-up of a singer in reflected night light" in prompt
    assert "film grain" in prompt
    assert "Japanese 80s city pop music video" not in prompt
    assert "progression: opening pass through the night" not in prompt
    assert "scene event: late-night city movement" not in prompt


def test_plan_preview_builds_qwen_style_prompt_tokens():
    from ai_mv.core.stages.plan_mv import build_plan_preview_payload

    payload = build_plan_preview_payload(
        {"planning": {"max_shot_sec": 8.0}},
        {
            "concept_text": "Japanese 80s city pop",
            "audio_map": {
                "duration_sec": 32.0,
                "sections": [
                    {"label": "Intro", "name": "intro", "start_sec": 0.0, "end_sec": 8.0},
                    {"label": "Verse 1", "name": "verse_1", "start_sec": 8.0, "end_sec": 16.0},
                    {"label": "Chorus", "name": "chorus", "start_sec": 16.0, "end_sec": 24.0},
                    {"label": "Outro", "name": "outro", "start_sec": 24.0, "end_sec": 32.0},
                ],
            },
        },
    )

    prompt = payload["render_plan"][0]["prompt_polish"]
    assert "clean cel shading" in prompt
    assert "same protagonist" in prompt
    assert "motion-safe keyframe" in prompt
    assert "80s japanese city pop illustration" not in prompt
    assert "film grain" in prompt


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
            "render_plan": [
                {
                    "shot_id": "S001",
                    "render_mode": "i2v",
                    "prompt_seed": "night drive",
                    "clip_prompt_seed": "slow windshield drift",
                    "clip_positive_prompt": "slow windshield drift, stable motion, no abrupt pose change",
                }
            ],
            "still_results": [{"shot_id": "S001", "image": "D:/renders/S001.png"}],
        },
    )

    out = run_render_clips(stage_input)

    assert out.payload["clip_results"][0]["video"] == "D:/renders/S001_i2v.mp4"
    assert calls[0][1]["image"] == "D:/renders/S001.png"
    assert calls[0][1]["filename_prefix"] == "clips/S001_i2v"
    assert calls[0][1]["prompt_seed"] == "slow windshield drift"
    assert calls[0][1]["positive_prompt"] == "slow windshield drift, stable motion, no abrupt pose change"


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


def test_assemble_mv_propagates_review_quality_findings_path_from_config(monkeypatch, tmp_path):
    final_file = tmp_path / "artifacts" / "runs" / "run-3b" / "final" / "final_mv.mp4"
    findings_path = tmp_path / "manual-review" / "review-findings.json"

    def _fake_run_file(run_id, name, scope="run"):
        assert run_id == "run-3b"
        assert name == "final/final_mv.mp4"
        final_file.parent.mkdir(parents=True, exist_ok=True)
        return final_file

    def _fake_resolve_generated_file(_config, ref, _exts, _label):
        return Path(ref)

    def _fake_run_ffmpeg_mux(clips, audio, out, _config):
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b"video")
        return True

    monkeypatch.setattr("ai_mv.core.stages.assemble_mv.run_file", _fake_run_file)
    monkeypatch.setattr("ai_mv.core.stages.assemble_mv.resolve_generated_file", _fake_resolve_generated_file)
    monkeypatch.setattr("ai_mv.core.stages.assemble_mv.run_ffmpeg_mux", _fake_run_ffmpeg_mux)
    stage_input = StageInput(
        run_id="run-3b",
        config={"review": {"quality_findings_path": str(findings_path)}},
        payload={
            "music_file": str(tmp_path / "music.mp3"),
            "clip_results": [{"shot_id": "S001", "video": str(tmp_path / "clip.mp4")}],
        },
    )

    out = run_assemble_mv(stage_input)

    assert out.payload["review_inputs"]["quality_findings_path"] == str(findings_path)


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


def test_review_outputs_honors_explicit_quality_findings(monkeypatch):
    existing = {"D:/renders/final.mp4", "D:/renders/S006.png", "D:/renders/S006.mp4"}

    def _fake_exists(self):
        return str(self).replace("\\", "/") in {path.replace("\\", "/") for path in existing}

    from pathlib import Path as _Path

    _original_exists = _Path.exists
    _Path.exists = _fake_exists
    try:
        stage_input = StageInput(
            run_id="run-9",
            config={},
            payload={
                "final_video": "D:/renders/final.mp4",
                "shot_plan": [{"shot_id": "S006"}],
                "still_results": [{"shot_id": "S006", "image": "D:/renders/S006.png", "status": "done"}],
                "clip_results": [{"shot_id": "S006", "video": "D:/renders/S006.mp4", "status": "done"}],
                "review_inputs": {
                    "music_file": "D:/renders/song.mp3",
                    "quality_findings": {
                        "S006": ["terminal_frame_corruption", "continuity_break"],
                    },
                },
            },
        )

        out = run_review_outputs(stage_input)

        assert out.payload["review_report"]["status"] == "needs_rerender"
        assert out.payload["review_report"]["rerender_targets"] == ["S006"]
        assert out.payload["review_report"]["blocking_checks"]["terminal_frames_clean"] is False
        assert out.payload["review_report"]["blocking_checks"]["visual_continuity_preserved"] is False
        assert out.payload["review_report"]["benchmark_dimensions"]["temporal_coherence"]["passed"] is False
        assert out.payload["review_report"]["benchmark_dimensions"]["temporal_coherence"]["affected_shots"] == ["S006"]
        assert out.payload["review_report"]["benchmark_dimensions"]["continuity"]["reasons"] == ["continuity_break"]
        assert out.payload["review_report"]["review_signal_buckets"]["heuristic_proxy"]["passed"] is False
        assert out.payload["review_report"]["review_signal_buckets"]["heuristic_proxy"]["failed_checks"] == ["terminal_frames_clean", "visual_continuity_preserved"]
        assert out.payload["review_report"]["review_signal_buckets"]["model_judged"]["passed"] is False
        assert out.payload["review_report"]["publishability_summary"]["technical_completion"]["passed"] is True
        assert out.payload["review_report"]["publishability_summary"]["technical_completion"]["next_action"] == "no_action"
        assert out.payload["review_report"]["publishability_summary"]["technical_completion"]["rerender_bundle"] == {
            "action": "no_action",
            "target_shots": [],
            "reason_codes": [],
        }
        assert out.payload["review_report"]["publishability_summary"]["isolated_asset_quality"]["passed"] is False
        assert out.payload["review_report"]["publishability_summary"]["isolated_asset_quality"]["next_action"] == "rerender_clips_with_terminal_frame_cleanup"
        assert out.payload["review_report"]["publishability_summary"]["isolated_asset_quality"]["rerender_bundle"] == {
            "action": "rerender_clips_with_terminal_frame_cleanup",
            "target_shots": ["S006"],
            "reason_codes": ["terminal_frame_corruption"],
        }
        assert out.payload["review_report"]["publishability_summary"]["final_mv_publishability"]["passed"] is False
        assert out.payload["review_report"]["publishability_summary"]["final_mv_publishability"]["next_action"] == "rerender_continuity_break_shots"
        assert out.payload["review_report"]["publishability_summary"]["final_mv_publishability"]["rerender_bundle"] == {
            "action": "rerender_continuity_break_shots",
            "target_shots": ["S006"],
            "reason_codes": ["continuity_break"],
        }
        assert out.payload["review_report"]["rerender_plan"] == [
            {
                "shot_id": "S006",
                "reason_codes": ["terminal_frame_corruption", "continuity_break"],
                "priority_score": out.payload["review_report"]["rerender_priority_scores"]["S006"],
                "bucket": "isolated_asset_quality",
                "recommended_action": "rerender_clips_with_terminal_frame_cleanup",
                "rerender_prescription": {
                    "stage_focus": "clips",
                    "workflow_focus": ["i2v", "ia2v", "flf2v"],
                    "prompt_contract_focus": ["clip_prompt_seed", "clip_positive_prompt"],
                    "fix_strategy": "shorter_motion_and_clean_terminal_frames",
                },
            }
        ]
        assert out.payload["review_report"]["rerender_payload"] == [
            {
                "shot_id": "S006",
                "quality_findings": ["terminal_frame_corruption", "continuity_break"],
                "rerender_stage": "clips",
                "workflow_focus": ["i2v", "ia2v", "flf2v"],
                "prompt_contract_focus": ["clip_prompt_seed", "clip_positive_prompt"],
                "recommended_action": "rerender_clips_with_terminal_frame_cleanup",
                "fix_strategy": "shorter_motion_and_clean_terminal_frames",
            }
        ]
        assert out.payload["review_report"]["rerender_execution_payloads"] == [
            {
                "shot_id": "S006",
                "recommended_action": "rerender_clips_with_terminal_frame_cleanup",
                "rerender_stage": "clips",
                "stage_payloads": {
                    "clips": {
                        "shot_plan": [{"shot_id": "S006"}],
                        "render_plan": [],
                        "still_results": [{"shot_id": "S006", "image": "D:/renders/S006.png", "status": "done"}],
                        "music_file": "",
                    }
                },
            }
        ]
    finally:
        _Path.exists = _original_exists



def test_review_outputs_loads_quality_findings_from_review_inputs_path(monkeypatch, tmp_path):
    findings_path = tmp_path / "review-findings.json"
    findings_path.write_text(
        '{\n'
        '  "review_inputs": {\n'
        '    "quality_findings": {\n'
        '      "S006": ["terminal_frame_corruption", "continuity_break"]\n'
        '    }\n'
        '  }\n'
        '}\n',
        encoding="utf-8",
    )
    existing = {"D:/renders/final.mp4", "D:/renders/S006.png", "D:/renders/S006.mp4", str(findings_path)}

    def _fake_exists(self):
        return str(self).replace("\\", "/") in {path.replace("\\", "/") for path in existing}

    from pathlib import Path as _Path

    _original_exists = _Path.exists
    _Path.exists = _fake_exists
    try:
        stage_input = StageInput(
            run_id="run-9b",
            config={},
            payload={
                "final_video": "D:/renders/final.mp4",
                "shot_plan": [{"shot_id": "S006"}],
                "still_results": [{"shot_id": "S006", "image": "D:/renders/S006.png", "status": "done"}],
                "clip_results": [{"shot_id": "S006", "video": "D:/renders/S006.mp4", "status": "done"}],
                "review_inputs": {
                    "music_file": "D:/renders/song.mp3",
                    "quality_findings_path": str(findings_path),
                },
            },
        )

        out = run_review_outputs(stage_input)

        assert out.payload["review_report"]["status"] == "needs_rerender"
        assert out.payload["review_report"]["rerender_targets"] == ["S006"]
        assert out.payload["review_report"]["blocking_checks"]["terminal_frames_clean"] is False
        assert out.payload["review_report"]["blocking_checks"]["visual_continuity_preserved"] is False
    finally:
        _Path.exists = _original_exists



def test_review_outputs_fails_when_configured_quality_findings_path_is_invalid(tmp_path):
    import pytest

    findings_path = tmp_path / "review-findings.json"
    findings_path.write_text('{"review_inputs": ', encoding="utf-8")
    stage_input = StageInput(
        run_id="run-9c",
        config={},
        payload={
            "final_video": "D:/renders/final.mp4",
            "shot_plan": [{"shot_id": "S006"}],
            "still_results": [{"shot_id": "S006", "image": "D:/renders/S006.png", "status": "done"}],
            "clip_results": [{"shot_id": "S006", "video": "D:/renders/S006.mp4", "status": "done"}],
            "review_inputs": {
                "music_file": "D:/renders/song.mp3",
                "quality_findings_path": str(findings_path),
            },
        },
    )

    with pytest.raises(RuntimeError, match="invalid review quality findings file"):
        run_review_outputs(stage_input)



def test_prepare_rerender_aggregates_review_execution_payloads_into_stage_inputs():
    stage_input = StageInput(
        run_id="run-rerender-1",
        config={},
        payload={
            "review_report": {
                "rerender_execution_payloads": [
                    {
                        "shot_id": "S003",
                        "recommended_action": "rerender_scene_intrusion_shots",
                        "rerender_stage": "stills",
                        "stage_payloads": {
                            "stills": {
                                "shot_plan": [{"shot_id": "S003", "render_mode": "i2v"}],
                                "render_plan": [{"shot_id": "S003", "render_mode": "i2v", "still_prompt_text": "still-3"}],
                            }
                        },
                    },
                    {
                        "shot_id": "S001",
                        "recommended_action": "rerender_panelized_keyframes",
                        "rerender_stage": "stills",
                        "stage_payloads": {
                            "stills": {
                                "shot_plan": [{"shot_id": "S001", "render_mode": "i2v"}],
                                "render_plan": [{"shot_id": "S001", "render_mode": "i2v", "still_prompt_text": "still-1"}],
                            }
                        },
                    },
                    {
                        "shot_id": "S002",
                        "recommended_action": "rerender_motion_fragile_shots_with_safer_keyframes",
                        "rerender_stage": "stills_then_clips",
                        "stage_payloads": {
                            "stills": {
                                "shot_plan": [{"shot_id": "S002", "render_mode": "flf2v", "bridge_to_shot_id": "S004"}],
                                "render_plan": [{"shot_id": "S002", "render_mode": "flf2v", "still_b": "S004", "clip_prompt_seed": "clip-2"}],
                            },
                            "clips": {
                                "shot_plan": [{"shot_id": "S002", "render_mode": "flf2v", "bridge_to_shot_id": "S004"}],
                                "render_plan": [{"shot_id": "S002", "render_mode": "flf2v", "still_b": "S004", "clip_prompt_seed": "clip-2"}],
                                "still_results": [
                                    {"shot_id": "S002", "image": "still-2.png"},
                                    {"shot_id": "S004", "image": "still-4.png"},
                                ],
                                "music_file": "song.mp3",
                            },
                        },
                    },
                    {
                        "shot_id": "S006",
                        "recommended_action": "rerender_clips_with_terminal_frame_cleanup",
                        "rerender_stage": "clips",
                        "stage_payloads": {
                            "clips": {
                                "shot_plan": [{"shot_id": "S006", "render_mode": "i2v"}],
                                "render_plan": [{"shot_id": "S006", "render_mode": "i2v", "clip_prompt_seed": "clip-6"}],
                                "still_results": [{"shot_id": "S006", "image": "still-6.png"}],
                                "music_file": "",
                            }
                        },
                    },
                ]
            }
        },
    )

    out = run_prepare_rerender(stage_input)

    assert out.stage == "prepare_rerender"
    assert out.status == "done"
    assert out.payload == {
        "rerender_target_ids": ["S003", "S001", "S002", "S006"],
        "rerender_stage_sequence": ["stills", "clips"],
        "rerender_stage_inputs": {
            "stills": {
                "shot_plan": [
                    {"shot_id": "S003", "render_mode": "i2v"},
                    {"shot_id": "S001", "render_mode": "i2v"},
                    {"shot_id": "S002", "render_mode": "flf2v", "bridge_to_shot_id": "S004"},
                ],
                "render_plan": [
                    {"shot_id": "S003", "render_mode": "i2v", "still_prompt_text": "still-3"},
                    {"shot_id": "S001", "render_mode": "i2v", "still_prompt_text": "still-1"},
                    {"shot_id": "S002", "render_mode": "flf2v", "still_b": "S004", "clip_prompt_seed": "clip-2"},
                ],
            },
            "clips": {
                "shot_plan": [
                    {"shot_id": "S002", "render_mode": "flf2v", "bridge_to_shot_id": "S004"},
                    {"shot_id": "S006", "render_mode": "i2v"},
                ],
                "render_plan": [
                    {"shot_id": "S002", "render_mode": "flf2v", "still_b": "S004", "clip_prompt_seed": "clip-2"},
                    {"shot_id": "S006", "render_mode": "i2v", "clip_prompt_seed": "clip-6"},
                ],
                "still_results": [
                    {"shot_id": "S002", "image": "still-2.png"},
                    {"shot_id": "S004", "image": "still-4.png"},
                    {"shot_id": "S006", "image": "still-6.png"},
                ],
                "music_file": "song.mp3",
            },
        },
    }



def test_prepare_rerender_returns_empty_stage_inputs_when_review_has_no_targets():
    stage_input = StageInput(
        run_id="run-rerender-empty",
        config={},
        payload={"review_report": {"rerender_execution_payloads": []}},
    )

    out = run_prepare_rerender(stage_input)

    assert out.payload == {
        "rerender_target_ids": [],
        "rerender_stage_sequence": [],
        "rerender_stage_inputs": {},
    }



def test_execute_rerender_runs_stills_then_clips_with_fresh_still_results(monkeypatch):
    calls = []

    def _fake_run_render_stills(stage_input):
        calls.append(("stills", stage_input.payload))
        return StageOutput("render_stills", "done", {"still_results": [{"shot_id": "S002", "image": "rerendered-2.png"}]}, [])

    def _fake_run_render_clips(stage_input):
        calls.append(("clips", stage_input.payload))
        return StageOutput("render_clips", "done", {"clip_results": [{"shot_id": "S002", "video": "rerendered-2.mp4"}]}, [])

    monkeypatch.setattr("ai_mv.core.stages.execute_rerender.run_render_stills", _fake_run_render_stills)
    monkeypatch.setattr("ai_mv.core.stages.execute_rerender.run_render_clips", _fake_run_render_clips)

    stage_input = StageInput(
        run_id="run-rerender-exec-1",
        config={"render": {"ltx_fps": 24}},
        payload={
            "rerender_stage_sequence": ["stills", "clips"],
            "rerender_stage_inputs": {
                "stills": {
                    "shot_plan": [{"shot_id": "S002", "render_mode": "flf2v"}],
                    "render_plan": [{"shot_id": "S002", "render_mode": "flf2v", "still_prompt_text": "repair still"}],
                },
                "clips": {
                    "shot_plan": [{"shot_id": "S002", "render_mode": "flf2v", "bridge_to_shot_id": "S004"}],
                    "render_plan": [{"shot_id": "S002", "render_mode": "flf2v", "still_b": "S004", "clip_prompt_seed": "repair clip"}],
                    "still_results": [
                        {"shot_id": "S002", "image": "stale-2.png"},
                        {"shot_id": "S004", "image": "bridge-4.png"},
                    ],
                    "music_file": "song.mp3",
                },
            },
        },
    )

    out = run_execute_rerender(stage_input)

    assert [name for name, _payload in calls] == ["stills", "clips"]
    assert calls[1][1]["still_results"] == [
        {"shot_id": "S004", "image": "bridge-4.png"},
        {"shot_id": "S002", "image": "rerendered-2.png"},
    ]
    assert out.stage == "execute_rerender"
    assert out.status == "done"
    assert out.payload == {
        "rerender_results": {
            "completed_stages": ["stills", "clips"],
            "still_results": [{"shot_id": "S002", "image": "rerendered-2.png"}],
            "clip_results": [{"shot_id": "S002", "video": "rerendered-2.mp4"}],
        }
    }



def test_execute_rerender_returns_empty_results_when_no_rerender_stage_inputs_exist():
    out = run_execute_rerender(
        StageInput(
            run_id="run-rerender-exec-empty",
            config={},
            payload={"rerender_stage_sequence": [], "rerender_stage_inputs": {}},
        )
    )

    assert out.payload == {
        "rerender_results": {
            "completed_stages": [],
            "still_results": [],
            "clip_results": [],
        }
    }



def test_rerender_review_merges_fresh_assets_and_recomputes_review(monkeypatch):
    existing = {"D:/renders/final.mp4", "D:/renders/S001_retry.png", "D:/renders/S001_retry.mp4"}

    def _fake_exists(self):
        return str(self).replace("\\", "/") in {path.replace("\\", "/") for path in existing}

    from pathlib import Path as _Path

    _original_exists = _Path.exists
    _Path.exists = _fake_exists
    try:
        stage_input = StageInput(
            run_id="run-rerender-review-1",
            config={},
            payload={
                "final_video": "D:/renders/final.mp4",
                "music_file": "D:/renders/song.mp3",
                "shot_plan": [{"shot_id": "S001"}],
                "render_plan": [{"shot_id": "S001", "render_mode": "i2v"}],
                "still_results": [{"shot_id": "S001", "image": "", "status": "failed"}],
                "clip_results": [{"shot_id": "S001", "video": "", "status": "failed"}],
                "review_inputs": {"music_file": "D:/renders/song.mp3", "quality_findings": {"S001": []}},
                "rerender_results": {
                    "completed_stages": ["stills", "clips"],
                    "still_results": [{"shot_id": "S001", "image": "D:/renders/S001_retry.png", "status": "done"}],
                    "clip_results": [{"shot_id": "S001", "video": "D:/renders/S001_retry.mp4", "status": "done"}],
                },
            },
        )

        out = run_rerender_review(stage_input)

        assert out.stage == "rerender_review"
        assert out.status == "done"
        assert out.payload["still_results"] == [{"shot_id": "S001", "image": "D:/renders/S001_retry.png", "status": "done"}]
        assert out.payload["clip_results"] == [{"shot_id": "S001", "video": "D:/renders/S001_retry.mp4", "status": "done"}]
        assert out.payload["rerender_review_report"]["status"] == "done"
        assert out.payload["rerender_review_report"]["rerender_targets"] == []
    finally:
        _Path.exists = _original_exists



def test_rerender_review_keeps_existing_assets_for_unmodified_shots():
    out = run_rerender_review(
        StageInput(
            run_id="run-rerender-review-2",
            config={},
            payload={
                "shot_plan": [{"shot_id": "S001"}, {"shot_id": "S002"}],
                "still_results": [
                    {"shot_id": "S001", "image": "still-1.png", "status": "done"},
                    {"shot_id": "S002", "image": "still-2.png", "status": "done"},
                ],
                "clip_results": [
                    {"shot_id": "S001", "video": "clip-1.mp4", "status": "done"},
                    {"shot_id": "S002", "video": "clip-2.mp4", "status": "done"},
                ],
                "rerender_results": {
                    "completed_stages": ["stills"],
                    "still_results": [{"shot_id": "S001", "image": "still-1-retry.png", "status": "done"}],
                    "clip_results": [],
                },
            },
        )
    )

    assert out.payload["still_results"] == [
        {"shot_id": "S002", "image": "still-2.png", "status": "done"},
        {"shot_id": "S001", "image": "still-1-retry.png", "status": "done"},
    ]
    assert out.payload["clip_results"] == [
        {"shot_id": "S001", "video": "clip-1.mp4", "status": "done"},
        {"shot_id": "S002", "video": "clip-2.mp4", "status": "done"},
    ]



def test_repair_rerender_prompts_applies_fix_strategies_to_stage_inputs():
    stage_input = StageInput(
        run_id="run-rerender-repair-1",
        config={},
        payload={
            "review_report": {
                "rerender_execution_payloads": [
                    {
                        "shot_id": "S001",
                        "recommended_action": "rerender_panelized_keyframes",
                        "rerender_stage": "stills",
                        "fix_strategy": "enforce_single_frame_keyframe_composition",
                        "prompt_contract_focus": ["still_prompt_text"],
                        "stage_payloads": {},
                    },
                    {
                        "shot_id": "S002",
                        "recommended_action": "rerender_scene_intrusion_shots",
                        "rerender_stage": "stills_then_clips",
                        "fix_strategy": "tighten_subject_and_world_anchors",
                        "prompt_contract_focus": ["still_prompt_text"],
                        "stage_payloads": {},
                    },
                    {
                        "shot_id": "S004",
                        "recommended_action": "rerender_weak_shots_with_prompt_tightening",
                        "rerender_stage": "stills",
                        "fix_strategy": "tighten_subject_identity_anchors",
                        "prompt_contract_focus": ["still_prompt_text"],
                        "stage_payloads": {},
                    },
                    {
                        "shot_id": "S005",
                        "recommended_action": "rerender_weak_shots_with_prompt_tightening",
                        "rerender_stage": "stills_then_clips",
                        "fix_strategy": "tighten_identity_continuity_anchors",
                        "prompt_contract_focus": ["still_prompt_text", "clip_prompt_seed", "clip_positive_prompt"],
                        "stage_payloads": {},
                    },
                    {
                        "shot_id": "S003",
                        "recommended_action": "rerender_clips_with_terminal_frame_cleanup",
                        "rerender_stage": "clips",
                        "fix_strategy": "shorter_motion_and_clean_terminal_frames",
                        "prompt_contract_focus": ["clip_prompt_seed", "clip_positive_prompt"],
                        "stage_payloads": {},
                    },
                ]
            },
            "rerender_stage_inputs": {
                "stills": {
                    "shot_plan": [{"shot_id": "S001"}, {"shot_id": "S002"}, {"shot_id": "S004"}, {"shot_id": "S005"}],
                    "render_plan": [
                        {"shot_id": "S001", "still_prompt_text": "neon portrait"},
                        {"shot_id": "S002", "still_prompt_text": "night street singer"},
                        {"shot_id": "S004", "still_prompt_text": "rooftop heroine close-up"},
                        {"shot_id": "S005", "still_prompt_text": "subway reflection heroine"},
                    ],
                },
                "clips": {
                    "shot_plan": [{"shot_id": "S003"}, {"shot_id": "S005"}],
                    "render_plan": [
                        {
                            "shot_id": "S003",
                            "clip_prompt_seed": "camera drift forward, stable motion, preserve subject continuity",
                            "clip_positive_prompt": "camera drift forward, stable motion, preserve subject continuity, single continuous motion, no abrupt pose change",
                        },
                        {
                            "shot_id": "S005",
                            "clip_prompt_seed": "subway sidestep motion, keep protagonist recognizable",
                            "clip_positive_prompt": "subway sidestep motion, keep protagonist recognizable, stable body silhouette, no abrupt pose change",
                        }
                    ],
                    "still_results": [],
                    "music_file": "song.mp3",
                },
            },
        },
    )

    out = run_repair_rerender_prompts(stage_input)

    still_rows = out.payload["rerender_stage_inputs"]["stills"]["render_plan"]
    clip_rows = out.payload["rerender_stage_inputs"]["clips"]["render_plan"]
    assert still_rows[0]["still_prompt_text"] == "neon portrait, single cinematic keyframe, one uninterrupted composition, no panel layout, no collage, no split screen"
    assert still_rows[1]["still_prompt_text"] == "night street singer, same protagonist, same environment, locked world details, no unrelated scene intrusion"
    assert still_rows[2]["still_prompt_text"] == "rooftop heroine close-up, same protagonist, locked identity details, no identity drift, no duplicate subject"
    assert still_rows[3]["still_prompt_text"] == "subway reflection heroine, same protagonist, continuity-locked identity details, match adjacent shots, no identity drift, preserve neighboring-shot continuity"
    assert clip_rows[0]["clip_prompt_seed"] == "camera drift forward, clean terminal frame, restrained motion range"
    assert clip_rows[0]["clip_positive_prompt"] == "camera drift forward, clean terminal frame, restrained motion range, shorter motion beat, clean exit frame, no abrupt pose change"
    assert clip_rows[1]["clip_prompt_seed"] == "subway sidestep motion, same protagonist, preserve neighboring-shot continuity"
    assert clip_rows[1]["clip_positive_prompt"] == "subway sidestep motion, same protagonist, preserve neighboring-shot continuity, match adjacent shots, no identity drift, no abrupt pose change"



def test_repair_rerender_prompts_leaves_inputs_unchanged_when_no_execution_payloads_exist():
    stage_input = StageInput(
        run_id="run-rerender-repair-empty",
        config={},
        payload={
            "review_report": {"rerender_execution_payloads": []},
            "rerender_stage_inputs": {
                "stills": {
                    "shot_plan": [{"shot_id": "S001"}],
                    "render_plan": [{"shot_id": "S001", "still_prompt_text": "keep me"}],
                }
            },
        },
    )

    out = run_repair_rerender_prompts(stage_input)

    assert out.payload["rerender_stage_inputs"] == stage_input.payload["rerender_stage_inputs"]



def test_rerender_loop_chains_prepare_repair_execute_and_review(monkeypatch):
    calls = []

    def _fake_prepare(stage_input):
        calls.append(("prepare", dict(stage_input.payload)))
        return StageOutput(
            "prepare_rerender",
            "done",
            {
                "rerender_stage_sequence": ["stills"],
                "rerender_stage_inputs": {
                    "stills": {
                        "shot_plan": [{"shot_id": "S001"}],
                        "render_plan": [{"shot_id": "S001", "still_prompt_text": "draft"}],
                    }
                },
            },
            [],
        )

    def _fake_repair(stage_input):
        calls.append(("repair", dict(stage_input.payload)))
        assert stage_input.payload["rerender_stage_inputs"]["stills"]["render_plan"][0]["still_prompt_text"] == "draft"
        return StageOutput(
            "repair_rerender_prompts",
            "done",
            {
                "rerender_stage_inputs": {
                    "stills": {
                        "shot_plan": [{"shot_id": "S001"}],
                        "render_plan": [{"shot_id": "S001", "still_prompt_text": "repaired"}],
                    }
                }
            },
            [],
        )

    def _fake_execute(stage_input):
        calls.append(("execute", dict(stage_input.payload)))
        assert stage_input.payload["rerender_stage_inputs"]["stills"]["render_plan"][0]["still_prompt_text"] == "repaired"
        return StageOutput(
            "execute_rerender",
            "done",
            {
                "rerender_results": {
                    "completed_stages": ["stills"],
                    "still_results": [{"shot_id": "S001", "image": "retry.png", "status": "done"}],
                    "clip_results": [],
                }
            },
            [],
        )

    def _fake_review(stage_input):
        calls.append(("review", dict(stage_input.payload)))
        assert stage_input.payload["rerender_results"]["still_results"] == [{"shot_id": "S001", "image": "retry.png", "status": "done"}]
        return StageOutput(
            "rerender_review",
            "done",
            {
                "still_results": [{"shot_id": "S001", "image": "retry.png", "status": "done"}],
                "clip_results": [],
                "rerender_review_report": {"status": "done", "rerender_targets": []},
            },
            [],
        )

    monkeypatch.setattr("ai_mv.core.stages.rerender_loop.run_prepare_rerender", _fake_prepare)
    monkeypatch.setattr("ai_mv.core.stages.rerender_loop.run_repair_rerender_prompts", _fake_repair)
    monkeypatch.setattr("ai_mv.core.stages.rerender_loop.run_execute_rerender", _fake_execute)
    monkeypatch.setattr("ai_mv.core.stages.rerender_loop.run_rerender_review", _fake_review)

    out = run_rerender_loop(
        StageInput(
            run_id="run-rerender-loop-1",
            config={},
            payload={"review_report": {"rerender_execution_payloads": [{"shot_id": "S001"}]}, "still_results": []},
        )
    )

    assert [name for name, _payload in calls] == ["prepare", "repair", "execute", "review"]
    assert out.stage == "rerender_loop"
    assert out.status == "done"
    assert out.payload["rerender_stage_inputs"]["stills"]["render_plan"][0]["still_prompt_text"] == "repaired"
    assert out.payload["rerender_results"]["still_results"] == [{"shot_id": "S001", "image": "retry.png", "status": "done"}]
    assert out.payload["rerender_review_report"] == {"status": "done", "rerender_targets": []}
    assert out.payload["rerender_outcome"] == {"attempted": True, "resolved": True, "exhausted": False}



def test_rerender_loop_marks_unresolved_rerender_outcome_when_review_still_fails(monkeypatch):
    monkeypatch.setattr(
        "ai_mv.core.stages.rerender_loop.run_prepare_rerender",
        lambda stage_input: StageOutput(
            "prepare_rerender",
            "done",
            {"rerender_stage_sequence": ["stills"], "rerender_stage_inputs": {"stills": {"shot_plan": [], "render_plan": []}}},
            [],
        ),
    )
    monkeypatch.setattr(
        "ai_mv.core.stages.rerender_loop.run_repair_rerender_prompts",
        lambda stage_input: StageOutput("repair_rerender_prompts", "done", {"rerender_stage_inputs": {"stills": {"shot_plan": [], "render_plan": []}}}, []),
    )
    monkeypatch.setattr(
        "ai_mv.core.stages.rerender_loop.run_execute_rerender",
        lambda stage_input: StageOutput("execute_rerender", "done", {"rerender_results": {"completed_stages": ["stills"], "still_results": [], "clip_results": []}}, []),
    )
    monkeypatch.setattr(
        "ai_mv.core.stages.rerender_loop.run_rerender_review",
        lambda stage_input: StageOutput(
            "rerender_review",
            "done",
            {
                "rerender_review_report": {"status": "needs_rerender", "rerender_targets": ["S009"]},
                "still_results": [],
                "clip_results": [],
            },
            [],
        ),
    )

    out = run_rerender_loop(StageInput(run_id="run-rerender-loop-fail", config={}, payload={"review_report": {"status": "needs_rerender"}}))

    assert out.payload["review_report"] == {"status": "needs_rerender", "rerender_targets": ["S009"]}
    assert out.payload["rerender_outcome"] == {"attempted": True, "resolved": False, "exhausted": True}



def test_rerender_escalation_builds_manual_review_packet_request(monkeypatch):
    monkeypatch.setattr(
        "ai_mv.core.stages.rerender_escalation.write_review_packet",
        lambda **kwargs: {
            "manifest_path": kwargs["output_dir"] / "review-packet.json",
            "quality_findings_path": kwargs["output_dir"] / "review-findings.json",
            "reviewer_notes_path": kwargs["output_dir"] / "review-notes.md",
            "contact_sheet_image_path": kwargs["output_dir"] / "contact-sheet.png",
            "contact_sheet_manifest_path": kwargs["output_dir"] / "contact-sheet.json",
        },
    )

    out = run_rerender_escalation(
        StageInput(
            run_id="run-rerender-escalate-1",
            config={},
            payload={
                "final_video": "D:/renders/final.mp4",
                "review_report": {
                    "rerender_targets": ["S003", "S007"],
                    "rerender_reasons": {
                        "S003": ["continuity_break", "identity_drift"],
                        "S007": ["terminal_frame_corruption"],
                    },
                    "rerender_plan": [
                        {
                            "shot_id": "S003",
                            "priority_score": 9,
                            "recommended_action": "rerender_continuity_break_shots",
                            "rerender_prescription": {
                                "stage_focus": "review",
                                "workflow_focus": None,
                                "prompt_contract_focus": [],
                                "fix_strategy": "inspect_review_failures_manually",
                            },
                        },
                        {
                            "shot_id": "S007",
                            "priority_score": 5,
                            "recommended_action": "rerender_clips_with_terminal_frame_cleanup",
                            "rerender_prescription": {
                                "stage_focus": "clips",
                                "workflow_focus": ["i2v", "ia2v", "flf2v"],
                                "prompt_contract_focus": ["clip_prompt_seed", "clip_positive_prompt"],
                                "fix_strategy": "shorter_motion_and_clean_terminal_frames",
                            },
                        },
                    ],
                },
                "rerender_outcome": {"attempted": True, "resolved": False, "exhausted": True},
            },
        )
    )

    report = out.payload["rerender_escalation"]
    assert report["status"] == "manual_review_required"
    assert report["shot_ids"] == ["S003", "S007"]
    assert report["shot_count"] == 2
    assert report["summary_by_shot"] == [
        {
            "shot_id": "S003",
            "reason_codes": ["continuity_break", "identity_drift"],
            "priority_score": 9,
            "recommended_action": "rerender_continuity_break_shots",
            "rerender_prescription": {
                "stage_focus": "review",
                "workflow_focus": None,
                "prompt_contract_focus": [],
                "fix_strategy": "inspect_review_failures_manually",
            },
            "packet_artifacts": report["artifacts"],
            "reviewer_note": "Inspect shot S003 in the review packet artifacts (reasons: continuity_break, identity_drift)",
        },
        {
            "shot_id": "S007",
            "reason_codes": ["terminal_frame_corruption"],
            "priority_score": 5,
            "recommended_action": "rerender_clips_with_terminal_frame_cleanup",
            "rerender_prescription": {
                "stage_focus": "clips",
                "workflow_focus": ["i2v", "ia2v", "flf2v"],
                "prompt_contract_focus": ["clip_prompt_seed", "clip_positive_prompt"],
                "fix_strategy": "shorter_motion_and_clean_terminal_frames",
            },
            "packet_artifacts": report["artifacts"],
            "reviewer_note": "Inspect shot S007 in the review packet artifacts (reasons: terminal_frame_corruption)",
        },
    ]
    assert report["video_path"] == "D:/renders/final.mp4"
    assert report["reviewer_summary"] == "Manual review required for 2 shots: S003, S007"
    assert report["review_packet_manifest_path"].endswith("review-packet.json")
    assert report["quality_findings_path"].endswith("review-findings.json")
    assert report["reviewer_notes_path"].endswith("review-notes.md")
    assert report["contact_sheet_image_path"].endswith("contact-sheet.png")
    assert report["contact_sheet_manifest_path"].endswith("contact-sheet.json")
    assert report["artifacts"] == {
        "review_packet_manifest": report["review_packet_manifest_path"],
        "quality_findings": report["quality_findings_path"],
        "reviewer_notes": report["reviewer_notes_path"],
        "contact_sheet_image": report["contact_sheet_image_path"],
        "contact_sheet_manifest": report["contact_sheet_manifest_path"],
    }
    assert out.artifacts == [
        report["review_packet_manifest_path"],
        report["quality_findings_path"],
        report["reviewer_notes_path"],
        report["contact_sheet_image_path"],
        report["contact_sheet_manifest_path"],
    ]



def test_rerender_escalation_skips_packet_creation_when_not_exhausted(monkeypatch):
    called = []
    monkeypatch.setattr(
        "ai_mv.core.stages.rerender_escalation.write_review_packet",
        lambda **kwargs: called.append(True),
    )

    out = run_rerender_escalation(
        StageInput(
            run_id="run-rerender-escalate-2",
            config={},
            payload={
                "final_video": "D:/renders/final.mp4",
                "review_report": {"rerender_targets": ["S003"]},
                "rerender_outcome": {"attempted": True, "resolved": True, "exhausted": False},
            },
        )
    )

    assert called == []
    assert out.payload["rerender_escalation"] == {"status": "not_required", "shot_ids": [], "video_path": "D:/renders/final.mp4"}



def test_rerender_loop_returns_original_payload_when_no_rerender_targets_exist(monkeypatch):
    seen_prepare = []

    def _fake_prepare(stage_input):
        seen_prepare.append(True)
        return StageOutput("prepare_rerender", "done", {"rerender_stage_sequence": [], "rerender_stage_inputs": {}}, [])

    monkeypatch.setattr("ai_mv.core.stages.rerender_loop.run_prepare_rerender", _fake_prepare)

    out = run_rerender_loop(
        StageInput(
            run_id="run-rerender-loop-empty",
            config={},
            payload={"review_report": {"rerender_execution_payloads": []}, "still_results": [{"shot_id": "S001"}]},
        )
    )

    assert seen_prepare == [True]
    assert out.payload["rerender_stage_inputs"] == {}
    assert out.payload["rerender_stage_sequence"] == []
    assert out.payload["still_results"] == [{"shot_id": "S001"}]
