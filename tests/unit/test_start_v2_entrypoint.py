import ai_mv.entrypoints.start_v2 as entry


def test_run_start_v2_entry_reports_done(monkeypatch, capsys):
    monkeypatch.setattr(entry, "acquire_lock", lambda _name: object())
    monkeypatch.setattr(entry, "release_lock", lambda _lock: None)
    monkeypatch.setattr(entry, "_load_prepared_config", lambda brief: {"brief": brief or "director_brief_example"})
    monkeypatch.setattr(entry, "run_doctor", lambda _cfg: 0)
    monkeypatch.setattr(entry, "_prepare_run_brief", lambda _cfg, _run_id: "v2-run")
    monkeypatch.setattr(entry, "run_pipeline_v2", lambda _cfg, _rid, allow_existing_run=True: "v2-run")
    monkeypatch.setattr(
        entry,
        "read_snapshot",
        lambda _rid: {"status": "done", "failure_reason": ""},
    )

    rc = entry.run_start_v2(brief="director_brief_example")
    out = capsys.readouterr().out

    assert rc == 0
    assert "run_id=v2-run" in out
    assert "status=done" in out

