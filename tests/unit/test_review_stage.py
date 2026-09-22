from pathlib import Path

from ai_mv.core.contracts.stage_io import StageInput
from ai_mv.core.stages.review_stage import run_review_stage


def test_review_stage_accepts_injected_duration_fn(monkeypatch):
    existing = {Path("D:/renders/final.mp4"), Path("D:/renders/song.mp3"), Path("D:/renders/S001.png"), Path("D:/renders/S001.mp4")}
    original_exists = Path.exists

    def _fake_exists(self):
        if self in existing:
            return True
        return original_exists(self)

    calls: list[str] = []

    def _fake_duration(path):
        calls.append(str(path))
        return 10.0 if str(path).endswith(".mp3") else 10.35

    monkeypatch.setattr(Path, "exists", _fake_exists)
    try:
        out = run_review_stage(
            StageInput(
                run_id="run-review-stage-duration-injection",
                config={"review": {"max_audio_video_drift_sec": 0.5}},
                payload={
                    "music_file": "D:/renders/song.mp3",
                    "final_video": "D:/renders/final.mp4",
                    "shot_plan": [{"shot_id": "S001"}],
                    "still_results": [{"shot_id": "S001", "image": "D:/renders/S001.png"}],
                    "clip_results": [{"shot_id": "S001", "video": "D:/renders/S001.mp4"}],
                },
            ),
            duration_fn=_fake_duration,
        )
    finally:
        monkeypatch.setattr(Path, "exists", original_exists)

    assert out.payload["review_report"]["audio_video_drift_sec"] == 0.35
    assert calls == ["D:/renders/song.mp3", "D:/renders/final.mp4"]


def test_review_stage_builds_material_aware_rerender_execution_payloads(monkeypatch):
    existing = {
        Path("D:/renders/final.mp4"),
        Path("D:/renders/song.mp3"),
        Path("D:/renders/S001.png"),
        Path("D:/renders/S001.mp4"),
    }
    original_exists = Path.exists

    def _fake_exists(self):
        if self in existing:
            return True
        return original_exists(self)

    monkeypatch.setattr(Path, "exists", _fake_exists)
    try:
        out = run_review_stage(
            StageInput(
                run_id="run-review-stage-material-aware-rerender",
                config={"review": {"max_audio_video_drift_sec": 0.5}},
                payload={
                    "music_file": "D:/renders/song.mp3",
                    "final_video": "D:/renders/final.mp4",
                    "style_bible": {"style": "synthwave"},
                    "shot_plan": [{"shot_id": "S001", "material_id": "MAT_001", "render_mode": "ia2v"}],
                    "material_plan": [{"material_id": "MAT_001", "section_id": "SEC_001"}],
                    "render_plan": [{"shot_id": "S001", "material_id": "MAT_001", "render_mode": "ia2v", "still_prompt_text": "hero frame"}],
                    "still_results": [{"shot_id": "S001", "image": "D:/renders/S001.png", "material_id": "MAT_001", "section_id": "SEC_001", "quality_issues": ["panel_layout"]}],
                    "clip_results": [{"shot_id": "S001", "video": "D:/renders/S001.mp4", "material_id": "MAT_001", "section_id": "SEC_001"}],
                    "review_inputs": {"music_file": "D:/renders/song.mp3"},
                },
            ),
            duration_fn=lambda path: 10.0 if str(path).endswith(".mp3") else 10.0,
        )
    finally:
        monkeypatch.setattr(Path, "exists", original_exists)

    assert out.payload["review_report"]["rerender_targets"] == ["S001"]
    assert out.payload["review_report"]["rerender_execution_payloads"] == [
        {
            "shot_id": "S001",
            "recommended_action": "rerender_panelized_keyframes",
            "rerender_stage": "stills",
            "execution_mode": "automatic",
            "workflow_focus": ["flux2_image"],
            "prompt_contract_focus": ["still_prompt_text"],
            "fix_strategy": "enforce_single_frame_keyframe_composition",
            "stage_payloads": {
                "stills": {
                    "shot_plan": [{"shot_id": "S001", "material_id": "MAT_001", "render_mode": "ia2v"}],
                    "material_plan": [{"material_id": "MAT_001", "section_id": "SEC_001"}],
                    "render_plan": [{"shot_id": "S001", "material_id": "MAT_001", "render_mode": "ia2v", "still_prompt_text": "hero frame"}],
                    "style_bible": {"style": "synthwave"},
                }
            },
        }
    ]
