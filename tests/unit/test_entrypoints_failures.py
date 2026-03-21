from pathlib import Path

from ai_mv.entrypoints import preflight


def test_run_preflight_entry_returns_clean_failure(monkeypatch, capsys):
    monkeypatch.setattr(preflight, "_load_prepared_config", lambda profile: {"profile": "x"})
    monkeypatch.setattr(preflight, "_prepare_run_profile", lambda cfg, run_id: "run-fail")
    monkeypatch.setattr(preflight, "run_preflight", lambda cfg, run_id, allow_existing_run=True: (_ for _ in ()).throw(RuntimeError("boom")))
    monkeypatch.setattr(preflight, "read_snapshot", lambda run_id, scope="auto": {"status": "failed", "failure_reason": "bad profile", "run_id": run_id})
    monkeypatch.setattr(preflight, "acquire_lock", lambda name: Path("artifacts/entrypoint.lock"))
    monkeypatch.setattr(preflight, "release_lock", lambda lock: None)

    assert preflight.run_preflight_entry("run-1", "x") == 1
    out = capsys.readouterr().out
    assert "status=failed" in out
    assert "failure_reason=bad profile" in out
