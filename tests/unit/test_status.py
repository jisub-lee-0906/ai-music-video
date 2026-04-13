from ai_mv.entrypoints.status import show_status


def test_show_status_missing_run_returns_failure_code(capsys):
    assert show_status("definitely-not-a-real-run-id") == 1
    assert "missing" in capsys.readouterr().out
