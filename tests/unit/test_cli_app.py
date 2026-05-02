import sys

from ai_mv.cli import app
from ai_mv.cli.args import build_parser


def test_build_parser_supports_start_command():
    parser = build_parser()

    args = parser.parse_args(["start", "--concept-text", "neon rain protagonist", "--run-id", "run-123"])

    assert args.command == "start"
    assert args.concept_text == "neon rain protagonist"
    assert args.run_id == "run-123"


def test_build_parser_supports_validate_latest_command():
    parser = build_parser()

    args = parser.parse_args(
        [
            "validate-latest",
            "--output-dir",
            ".analysis/latest-validation",
            "--sample-count",
            "8",
            "--shot-id",
            "S001",
        ]
    )

    assert args.command == "validate-latest"
    assert args.output_dir == ".analysis/latest-validation"
    assert args.sample_count == 8
    assert args.shot_ids == ["S001"]


def test_build_parser_rejects_removed_debug_commands():
    parser = build_parser()

    try:
        parser.parse_args(["review-packet", "--video", "renders/final.mp4"])
        raised = False
    except SystemExit:
        raised = True

    assert raised


def test_main_handles_dispatch_error(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["ai-mv", "start", "--run-id", "bad/run-id"])

    def raise_runtime(*args, **kwargs):
        raise RuntimeError("invalid run_id")

    monkeypatch.setattr(app, "dispatch", raise_runtime)

    rc = app.main()

    captured = capsys.readouterr()
    assert rc == 1
    assert "error: invalid run_id" in captured.err
