from pathlib import Path

import yaml

import ai_mv.core.orchestration.pipeline as pipeline_mod
from ai_mv.core.contracts.stage_io import StageOutput
from ai_mv.core.orchestration.pipeline import run_pipeline


def test_pipeline_smoke(monkeypatch):
    monkeypatch.setattr(pipeline_mod, "schedule", _fake_schedule)
    cfg = yaml.safe_load(Path("configs/default.yaml").read_text(encoding="utf-8"))
    cfg["runtime"]["template_hash_lock"] = False
    temp_cfg = Path("artifacts/reports/test-smoke-config.yaml")
    temp_cfg.parent.mkdir(parents=True, exist_ok=True)
    temp_cfg.write_text(yaml.safe_dump(cfg), encoding="utf-8")
    rid = run_pipeline(str(temp_cfg), "test-smoke")
    assert rid == "test-smoke"


def _fake_schedule():
    return [("fake_stage", _fake_stage)]


def _fake_stage(_stage_input):
    payload = {
        "anchors": [],
        "uso_images": [],
        "clips": [],
        "merge_status": "done",
        "final_video": "x.mp4",
        "quality_score": 0.0,
    }
    return StageOutput("fake_stage", "done", payload, [])
