import shutil
from pathlib import Path

import ai_mv.entrypoints.start as start_mod
from ai_mv.entrypoints.start import run_start


def test_start_smoke(monkeypatch):
    monkeypatch.setattr(start_mod, "run_doctor", lambda _cfg: 0)
    monkeypatch.setattr(start_mod, "run_pipeline", lambda _rid, allow_existing_run=False: "test-start")
    monkeypatch.setattr(
        start_mod,
        "read_snapshot",
        lambda _rid: {"status": "done", "failure_reason": "", "completed_stages": []},
    )
    shutil.rmtree(Path("artifacts/runs_state/test-start"), ignore_errors=True)
    assert run_start("test-start") == 0


def test_start_does_not_reserve_run_id_when_doctor_fails(monkeypatch):
    monkeypatch.setattr(start_mod, "run_doctor", lambda _cfg: 1)
    run_dir = Path("artifacts/runs_state/test-start-fail")
    shutil.rmtree(run_dir, ignore_errors=True)
    assert run_start("test-start-fail") == 1
    assert not run_dir.exists()
