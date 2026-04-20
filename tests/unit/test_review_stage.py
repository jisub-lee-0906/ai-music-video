from pathlib import Path

from ai_mv.core.contracts.stage_io import StageInput
from ai_mv.core.stages.review_stage import run_review_stage



def test_review_stage_accepts_injected_duration_fn(monkeypatch):
    existing = {"D:/renders/final.mp4", "D:/renders/song.mp3", "D:/renders/S001.png", "D:/renders/S001.mp4"}
    original_exists = Path.exists

    def _fake_exists(self):
        if str(self) in existing:
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
