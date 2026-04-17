import sys

from ai_mv.cli import app
from ai_mv.cli.args import build_parser


def test_build_parser_supports_extract_frames_command():
    parser = build_parser()

    args = parser.parse_args(
        [
            "extract-frames",
            "--video",
            "renders/final.mp4",
            "--output-dir",
            ".analysis/run-1",
            "--kind",
            "final",
            "--sample-count",
            "8",
        ]
    )

    assert args.command == "extract-frames"
    assert args.video == "renders/final.mp4"
    assert args.output_dir == ".analysis/run-1"
    assert args.kind == "final"
    assert args.sample_count == 8


def test_build_parser_supports_quality_findings_template_command():
    parser = build_parser()

    args = parser.parse_args(
        [
            "quality-findings-template",
            "--shot-id",
            "S001",
            "--shot-id",
            "S002",
            "--output",
            ".analysis/review-findings.json",
        ]
    )

    assert args.command == "quality-findings-template"
    assert args.shot_ids == ["S001", "S002"]
    assert args.output == ".analysis/review-findings.json"


def test_main_handles_dispatch_error(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["ai-mv", "start", "--run-id", "bad/run-id"])

    def raise_runtime(*args, **kwargs):
        raise RuntimeError("invalid run_id")

    monkeypatch.setattr(app, "dispatch", raise_runtime)

    rc = app.main()

    captured = capsys.readouterr()
    assert rc == 1
    assert "error: invalid run_id" in captured.err
