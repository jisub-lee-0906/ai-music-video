import sys

from ai_mv.cli import app


def test_main_handles_dispatch_error(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["ai-mv", "start", "--run-id", "bad/run-id"])

    def raise_runtime(*args, **kwargs):
        raise RuntimeError("invalid run_id")

    monkeypatch.setattr(app, "dispatch", raise_runtime)

    rc = app.main()

    captured = capsys.readouterr()
    assert rc == 1
    assert "error: invalid run_id" in captured.err
