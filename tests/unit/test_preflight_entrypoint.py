import ai_mv.entrypoints.preflight as entry


def test_run_preflight_entry_reports_done(monkeypatch, capsys):
    monkeypatch.setattr(entry, "acquire_lock", lambda _name: object())
    monkeypatch.setattr(entry, "release_lock", lambda _lock: None)
    monkeypatch.setattr(entry, "_load_prepared_config", lambda brief: {"brief": brief or "director_brief_example"})
    monkeypatch.setattr(entry, "_prepare_run_brief", lambda _cfg, _run_id: "run-123")
    monkeypatch.setattr(entry, "run_preflight", lambda _cfg, _rid, allow_existing_run=True: "run-123")

    rc = entry.run_preflight_entry(brief="director_brief_example")
    out = capsys.readouterr().out

    assert rc == 0
    assert "run_id=run-123" in out
    assert "status=done" in out
