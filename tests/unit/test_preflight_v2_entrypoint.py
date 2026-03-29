import ai_mv.entrypoints.preflight_v2 as entry


def test_run_preflight_v2_entry_reports_done(monkeypatch, capsys):
    monkeypatch.setattr(entry, "acquire_lock", lambda _name: object())
    monkeypatch.setattr(entry, "release_lock", lambda _lock: None)
    monkeypatch.setattr(entry, "_load_prepared_config", lambda brief: {"brief": brief or "director_brief_example"})
    monkeypatch.setattr(entry, "_prepare_run_brief", lambda _cfg, _run_id: "v2-run")
    monkeypatch.setattr(entry, "run_preflight_v2", lambda _cfg, _rid, allow_existing_run=True: "v2-run")

    rc = entry.run_preflight_v2_entry(brief="director_brief_example")
    out = capsys.readouterr().out

    assert rc == 0
    assert "run_id=v2-run" in out
    assert "status=done" in out
