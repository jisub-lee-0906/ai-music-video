from pathlib import Path

import pytest

from ai_mv.core.stages.media_resolver import build_merge_plan, resolve_audio_path, resolve_clip_paths


def test_resolve_clip_paths_raises_on_missing(tmp_path: Path):
    cfg = {"integrations": {"comfyui_output_dir": str(tmp_path / "out")}}
    run_dir = tmp_path / "run"
    run_dir.mkdir(parents=True, exist_ok=True)
    with pytest.raises(RuntimeError):
        resolve_clip_paths(["missing.mp4"], cfg, run_dir)


def test_resolve_audio_path_raises_on_missing(tmp_path: Path):
    cfg = {"integrations": {"comfyui_output_dir": str(tmp_path / "out")}}
    with pytest.raises(Exception):
        resolve_audio_path("missing.wav", cfg)


def test_build_merge_plan_adds_first_hold_and_head_tail_gaps():
    payload = {
        "clips": [
            {"shot_id": "s2", "video": "clip_2.mp4"},
            {"shot_id": "s3", "video": "clip_3.mp4"},
        ],
        "prompt_plan": {
            "wan_items": [
                {"shot_id": "s2", "start_ref_shot_id": "s1", "end_ref_shot_id": "s2"},
                {"shot_id": "s3", "start_ref_shot_id": "s2", "end_ref_shot_id": "s3"},
            ]
        },
        "flux2_ref_images": [
            {"shot_id": "s1", "end": "ref1.png"},
            {"shot_id": "s2", "end": "ref2.png"},
            {"shot_id": "s3", "end": "ref3.png"},
        ],
        "direction_plan": {
            "shot_packages": [
                {"shot_id": "s1", "start_sec": 8.0, "end_sec": 12.0, "duration_sec": 4.0},
                {"shot_id": "s2", "start_sec": 12.0, "end_sec": 16.0, "duration_sec": 4.0},
                {"shot_id": "s3", "start_sec": 16.0, "end_sec": 20.0, "duration_sec": 4.0},
            ]
        },
    }
    out = build_merge_plan(payload, audio_duration_sec=30.0)
    assert out["ordered"][0] == {"kind": "still", "image": "ref1.png", "duration_sec": 8.0, "label": "head_gap"}
    assert out["ordered"][1] == {"kind": "still", "image": "ref1.png", "duration_sec": 4.0, "label": "first_ref_hold"}
    assert out["ordered"][2] == {"kind": "video", "path": "clip_2.mp4", "label": "s2"}
    assert out["ordered"][3] == {"kind": "video", "path": "clip_3.mp4", "label": "s3"}
    assert out["ordered"][4] == {"kind": "still", "image": "ref3.png", "duration_sec": 10.0, "label": "tail_gap"}
