import shutil
from pathlib import Path

import yaml

import ai_mv.core.orchestration.pipeline as pipeline_mod
from ai_mv.core.contracts.stage_io import StageOutput
from ai_mv.core.orchestration.config_defaults import default_config
from ai_mv.core.orchestration.pipeline import run_pipeline


def test_pipeline_smoke(monkeypatch):
    monkeypatch.setattr(pipeline_mod, "schedule", _fake_schedule)
    cfg = default_config()
    cfg["runtime"]["template_hash_lock"] = False
    temp_cfg = Path("artifacts/reports/test-smoke-config.yaml")
    temp_cfg.parent.mkdir(parents=True, exist_ok=True)
    temp_cfg.write_text(yaml.safe_dump(cfg), encoding="utf-8")
    shutil.rmtree(Path("artifacts/runs_state/test-smoke"), ignore_errors=True)
    Path("artifacts/reports/test-smoke_summary.json").unlink(missing_ok=True)
    Path("artifacts/dashboards/test-smoke.json").unlink(missing_ok=True)
    rid = run_pipeline(str(temp_cfg), "test-smoke")
    assert rid == "test-smoke"


def test_pipeline_writes_initial_snapshot_before_first_stage(monkeypatch):
    seen = {"count": 0}

    def _fake_save_snapshot(_state, _payload):
        seen["count"] += 1

    def _fake_stage(_stage_input):
        assert seen["count"] == 2
        return StageOutput("fake_stage", "done", {"anchors": [], "uso_images": [], "clips": []}, [])

    monkeypatch.setattr(pipeline_mod, "schedule", lambda: [("fake_stage", _fake_stage)])
    monkeypatch.setattr(pipeline_mod, "save_snapshot", _fake_save_snapshot)
    cfg = default_config()
    cfg["runtime"]["template_hash_lock"] = False
    temp_cfg = Path("artifacts/reports/test-smoke-snapshot-config.yaml")
    temp_cfg.parent.mkdir(parents=True, exist_ok=True)
    temp_cfg.write_text(yaml.safe_dump(cfg), encoding="utf-8")
    shutil.rmtree(Path("artifacts/runs_state/test-smoke-snapshot"), ignore_errors=True)
    run_pipeline(str(temp_cfg), "test-smoke-snapshot")


def test_pipeline_writes_stage_name_before_stage_runs(monkeypatch):
    seen: list[str] = []

    def _fake_save_snapshot(state, _payload):
        seen.append(str(state.get("current_stage", "")))

    def _fake_stage(_stage_input):
        assert "fake_stage" in seen
        return StageOutput("fake_stage", "done", {"anchors": [], "uso_images": [], "clips": []}, [])

    monkeypatch.setattr(pipeline_mod, "schedule", lambda: [("fake_stage", _fake_stage)])
    monkeypatch.setattr(pipeline_mod, "save_snapshot", _fake_save_snapshot)
    cfg = default_config()
    cfg["runtime"]["template_hash_lock"] = False
    temp_cfg = Path("artifacts/reports/test-smoke-stage-config.yaml")
    temp_cfg.write_text(yaml.safe_dump(cfg), encoding="utf-8")
    shutil.rmtree(Path("artifacts/runs_state/test-smoke-stage"), ignore_errors=True)
    run_pipeline(str(temp_cfg), "test-smoke-stage")


def _fake_schedule():
    return [("fake_stage", _fake_stage)]


def _fake_stage(_stage_input):
    payload = {
        "anchors": [],
        "uso_images": [],
        "clips": [],
        "merge_status": "done",
        "final_video": "x.mp4",
    }
    return StageOutput("fake_stage", "done", payload, [])
