from ai_mv.cli.commands import dispatch


def test_dispatch_routes_start_command(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "ai_mv.cli.commands.run_start",
        lambda run_id=None, concept_text=None: calls.append((concept_text, run_id)) or 0,
    )

    rc = dispatch("start", concept_text="neon rain protagonist", run_id="run-123")

    assert rc == 0
    assert calls == [("neon rain protagonist", "run-123")]


def test_dispatch_routes_preflight_command(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "ai_mv.cli.commands.run_preflight_entry",
        lambda run_id=None, concept_text=None: calls.append((concept_text, run_id)) or 0,
    )

    rc = dispatch("preflight", concept_text="neon rain protagonist", run_id="run-123")

    assert rc == 0
    assert calls == [("neon rain protagonist", "run-123")]


def test_dispatch_routes_doctor_command(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "ai_mv.cli.commands.run_doctor",
        lambda cfg=None: calls.append(cfg) or 0,
    )

    rc = dispatch("doctor")

    assert rc == 0
    assert calls == [None]


def test_dispatch_routes_status_command(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "ai_mv.cli.commands.show_status",
        lambda run_id=None: calls.append(run_id) or 0,
    )

    rc = dispatch("status", run_id="run-123")

    assert rc == 0
    assert calls == ["run-123"]


def test_dispatch_routes_validate_latest_command(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "ai_mv.cli.commands.run_validate_latest",
        lambda output_dir, sample_count, shot_ids: calls.append((output_dir, sample_count, shot_ids)) or 0,
    )

    rc = dispatch(
        "validate-latest",
        output_dir=".analysis/latest-validation",
        sample_count=8,
        shot_ids=["S001"],
    )

    assert rc == 0
    assert calls == [(".analysis/latest-validation", 8, ["S001"])]


def test_dispatch_rejects_unknown_command():
    try:
        dispatch("unsupported-command")
        raised = False
    except ValueError as exc:
        raised = True
        assert "Unsupported command" in str(exc)

    assert raised
