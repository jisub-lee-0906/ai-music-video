import pytest

from ai_mv.core.contracts.stage_io import StageInput
from ai_mv.core.stages.render_clips import run_render_clips
from ai_mv.core.stages.render_stills import run_render_stills


def _base_clip_payload(still_row: dict, render_item: dict | None = None, shot: dict | None = None) -> dict:
    return {
        "music_file": "music/song.mp3",
        "shot_plan": [
            {
                "shot_id": "S001",
                "render_mode": "ia2v",
                "start_sec": 0.0,
                "duration_sec": 3.0,
                **(shot or {}),
            }
        ],
        "render_plan": [
            {
                "shot_id": "S001",
                "render_mode": "ia2v",
                "clip_prompt_seed": "slow cinematic motion, one protagonist only",
                **(render_item or {}),
            }
        ],
        "still_results": [
            {
                "shot_id": "S001",
                "image": "D:/renders/S001.png",
                "prompt_text": "same young woman in one continuous cinematic keyframe",
                **still_row,
            }
        ],
    }


def test_render_clips_blocks_still_with_explicit_qa_failure_before_ia2v(monkeypatch):
    calls = []

    def _fake_run_ltx_ia2v(_config, item):
        calls.append(dict(item))
        return f"D:/renders/{item['shot_id']}_ia2v.mp4"

    monkeypatch.setattr("ai_mv.core.stages.render_clips.run_ltx_ia2v", _fake_run_ltx_ia2v)
    stage_input = StageInput(
        run_id="run-still-qa-explicit-fail",
        config={"render": {"ltx_negative": "bad", "ltx_fps": 24, "ltx_default_shot_sec": 4.0}},
        payload=_base_clip_payload(
            {
                "still_qa": {
                    "status": "fail",
                    "blocking_reasons": ["duplicate_protagonist", "foreground_background_same_red_figure"],
                }
            }
        ),
    )

    with pytest.raises(RuntimeError, match="still QA blocked ia2v shot S001"):
        run_render_clips(stage_input)

    assert calls == []


def test_render_clips_blocks_clone_risk_prompt_before_ia2v(monkeypatch):
    calls = []

    def _fake_run_ltx_ia2v(_config, item):
        calls.append(dict(item))
        return f"D:/renders/{item['shot_id']}_ia2v.mp4"

    monkeypatch.setattr("ai_mv.core.stages.render_clips.run_ltx_ia2v", _fake_run_ltx_ia2v)
    stage_input = StageInput(
        run_id="run-still-qa-clone-risk",
        config={"render": {"ltx_negative": "bad", "ltx_fps": 24, "ltx_default_shot_sec": 4.0}},
        payload=_base_clip_payload(
            {
                "prompt_text": "same young woman, foreground protagonist plus a distant second red-coated figure in the background, double exposure look",
            }
        ),
    )

    with pytest.raises(RuntimeError) as exc:
        run_render_clips(stage_input)

    message = str(exc.value)
    assert "still QA blocked ia2v shot S001" in message
    assert "distant_second_red_figure" in message
    assert calls == []


def test_render_clips_blocks_microphone_action_without_matching_pose_anchor(monkeypatch):
    calls = []

    def _fake_run_ltx_ia2v(_config, item):
        calls.append(dict(item))
        return f"D:/renders/{item['shot_id']}_ia2v.mp4"

    monkeypatch.setattr("ai_mv.core.stages.render_clips.run_ltx_ia2v", _fake_run_ltx_ia2v)
    stage_input = StageInput(
        run_id="run-still-qa-microphone-mismatch",
        config={"render": {"ltx_negative": "bad", "ltx_fps": 24, "ltx_default_shot_sec": 4.0}},
        payload=_base_clip_payload(
            {
                "prompt_text": "same young woman singing into a handheld microphone on stage",
                "selected_pose_anchor_id": "ANCHOR_POSE_THREE_QUARTER_MEDIUM",
                "pose_anchor_selection": {"pose_family": "three_quarter", "intended_shot_functions": ["bridge"]},
            },
            render_item={"selected_pose_anchor_id": "ANCHOR_POSE_THREE_QUARTER_MEDIUM"},
            shot={"visual_mode": "chorus_microphone_performance", "story_function": "performance"},
        ),
    )

    with pytest.raises(RuntimeError) as exc:
        run_render_clips(stage_input)

    assert "unsupported_microphone_action" in str(exc.value)
    assert calls == []


def test_render_clips_allows_still_that_passes_qa_gate(monkeypatch):
    calls = []

    def _fake_run_ltx_ia2v(_config, item):
        calls.append(dict(item))
        return f"D:/renders/{item['shot_id']}_ia2v.mp4"

    monkeypatch.setattr("ai_mv.core.stages.render_clips.run_ltx_ia2v", _fake_run_ltx_ia2v)
    stage_input = StageInput(
        run_id="run-still-qa-pass",
        config={"render": {"ltx_negative": "bad", "ltx_fps": 24, "ltx_default_shot_sec": 4.0}},
        payload=_base_clip_payload(
            {
                "still_qa": {"status": "pass", "blocking_reasons": []},
                "selected_pose_anchor_id": "ANCHOR_POSE_HERO_CLOSEUP",
                "pose_anchor_selection": {"pose_family": "hero_closeup", "intended_shot_functions": ["performance"]},
            }
        ),
    )

    out = run_render_clips(stage_input)

    assert len(calls) == 1
    assert out.payload["clip_results"][0]["status"] == "done"


def test_render_clips_allows_microphone_action_with_microphone_pose_anchor(monkeypatch):
    calls = []

    def _fake_run_ltx_ia2v(_config, item):
        calls.append(dict(item))
        return f"D:/renders/{item['shot_id']}_ia2v.mp4"

    monkeypatch.setattr("ai_mv.core.stages.render_clips.run_ltx_ia2v", _fake_run_ltx_ia2v)
    stage_input = StageInput(
        run_id="run-still-qa-microphone-match",
        config={"render": {"ltx_negative": "bad", "ltx_fps": 24, "ltx_default_shot_sec": 4.0}},
        payload=_base_clip_payload(
            {
                "prompt_text": "same young woman singing into a handheld microphone, one uninterrupted composition",
                "selected_pose_anchor_id": "ANCHOR_POSE_MICROPHONE_PERFORMANCE",
                "pose_anchor_selection": {"pose_family": "microphone_performance", "intended_shot_functions": ["performance", "microphone"]},
            },
            render_item={"selected_pose_anchor_id": "ANCHOR_POSE_MICROPHONE_PERFORMANCE"},
            shot={"visual_mode": "chorus_microphone_performance", "story_function": "performance"},
        ),
    )

    out = run_render_clips(stage_input)

    assert len(calls) == 1
    assert out.payload["clip_results"][0]["status"] == "done"


def test_render_stills_publishes_still_qa_failure_metadata_for_clone_risk_prompt(monkeypatch):
    def _fake_run_flux2_still(_config, item):
        return f"D:/renders/{item['shot_id']}.png"

    monkeypatch.setattr("ai_mv.core.stages.render_stills.run_flux2_still", _fake_run_flux2_still)
    stage_input = StageInput(
        run_id="run-still-qa-publish-fail",
        config={"render": {"flux2_size": "1280x720"}},
        payload={
            "shot_plan": [{"shot_id": "S001", "render_mode": "ia2v"}],
            "render_plan": [
                {
                    "shot_id": "S001",
                    "render_mode": "ia2v",
                    "prompt_seed": "same young woman, foreground protagonist plus a distant second red-coated figure, double exposure look",
                }
            ],
        },
    )

    out = run_render_stills(stage_input)

    still_qa = out.payload["still_results"][0]["still_qa"]
    assert still_qa["status"] == "fail"
    assert "foreground_background_duplicate" in still_qa["blocking_reasons"]
    assert "distant_second_red_figure" in still_qa["blocking_reasons"]
    assert "double_exposure" in still_qa["blocking_reasons"]


def test_render_stills_publishes_still_qa_pass_metadata_for_clean_keyframe(monkeypatch):
    def _fake_run_flux2_still(_config, item):
        return f"D:/renders/{item['shot_id']}.png"

    monkeypatch.setattr("ai_mv.core.stages.render_stills.run_flux2_still", _fake_run_flux2_still)
    stage_input = StageInput(
        run_id="run-still-qa-publish-pass",
        config={"render": {"flux2_size": "1280x720"}},
        payload={
            "shot_plan": [{"shot_id": "S002", "render_mode": "ia2v"}],
            "render_plan": [
                {
                    "shot_id": "S002",
                    "render_mode": "ia2v",
                    "prompt_seed": "same young woman, one uninterrupted composition, medium cinematic close-up, no duplicate body",
                    "selected_pose_anchor_id": "ANCHOR_POSE_HERO_CLOSEUP",
                    "pose_anchor_selection": {"pose_family": "hero_closeup"},
                }
            ],
        },
    )

    out = run_render_stills(stage_input)

    still_qa = out.payload["still_results"][0]["still_qa"]
    assert still_qa == {"status": "pass", "blocking_reasons": []}
