from ai_mv.cli.commands import dispatch


def test_dispatch_routes_extract_frames_command(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "ai_mv.cli.commands.run_extract_frames",
        lambda video, output_dir, kind, sample_count: calls.append((video, output_dir, kind, sample_count)) or 0,
    )

    rc = dispatch(
        "extract-frames",
        video="renders/final.mp4",
        output_dir=".analysis/run-1",
        kind="final",
        sample_count=8,
    )

    assert rc == 0
    assert calls == [("renders/final.mp4", ".analysis/run-1", "final", 8)]


def test_dispatch_routes_quality_findings_template_command(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "ai_mv.cli.commands.run_quality_findings_template",
        lambda shot_ids, output: calls.append((shot_ids, output)) or 0,
    )

    rc = dispatch(
        "quality-findings-template",
        shot_ids=["S001", "S002"],
        output=".analysis/review-findings.json",
    )

    assert rc == 0
    assert calls == [(["S001", "S002"], ".analysis/review-findings.json")]
