import shutil
from pathlib import Path

import yaml

import ai_mv.core.orchestration.pipeline as pipeline_mod
from ai_mv.core.contracts.stage_io import StageOutput
from ai_mv.core.state.state_store import read_snapshot
from ai_mv.utils.json_utils import read_json


def test_pipeline_failure_writes_failure_artifacts(monkeypatch):
    monkeypatch.setattr(pipeline_mod, "schedule", _failing_schedule)
    cfg = yaml.safe_load(Path("configs/default.yaml").read_text(encoding="utf-8"))
    cfg["runtime"]["template_hash_lock"] = False
    temp_cfg = Path("artifacts/reports/test-fail-config.yaml")
    temp_cfg.parent.mkdir(parents=True, exist_ok=True)
    temp_cfg.write_text(yaml.safe_dump(cfg), encoding="utf-8")
    shutil.rmtree(Path("artifacts/runs_state/test-failed-run"), ignore_errors=True)
    for path in (
        Path("artifacts/reports/test-failed-run_summary.json"),
        Path("artifacts/runs_state/test-failed-run/manifest.json"),
        Path("artifacts/dashboards/test-failed-run.json"),
    ):
        path.unlink(missing_ok=True)

    run_id = pipeline_mod.run_pipeline(str(temp_cfg), "test-failed-run")

    snapshot = read_snapshot(run_id)
    assert snapshot["status"] == "failed"
    assert snapshot["failure_reason"] == "boom_stage: planned failure"

    summary = read_json(Path(f"artifacts/reports/{run_id}_summary.json"))
    manifest = read_json(Path(f"artifacts/runs_state/{run_id}/manifest.json"))
    dashboard = read_json(Path(f"artifacts/dashboards/{run_id}.json"))

    assert summary["failure_reason"] == "boom_stage: planned failure"
    assert manifest["status"] == "failed"
    assert dashboard["status"] == "failed"


def _failing_schedule():
    return [("ok_stage", _ok_stage), ("boom_stage", _boom_stage)]


def _ok_stage(_stage_input):
    payload = {
        "audio_map": {"duration_sec": 1.0, "sections": [{"name": "intro", "start_sec": 0.0, "end_sec": 1.0}]},
        "music_file": "song.mp3",
    }
    return StageOutput("ok_stage", "done", payload, [])


def _boom_stage(_stage_input):
    raise RuntimeError("planned failure")
