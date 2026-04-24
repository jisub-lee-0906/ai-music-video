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


def test_dispatch_routes_review_packet_command(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "ai_mv.cli.commands.run_review_packet",
        lambda video, output_dir, kind, sample_count, shot_ids: calls.append((video, output_dir, kind, sample_count, shot_ids)) or 0,
    )

    rc = dispatch(
        "review-packet",
        video="renders/final.mp4",
        output_dir=".analysis/run-1",
        kind="final",
        sample_count=8,
        shot_ids=["S001", "S002"],
    )

    assert rc == 0
    assert calls == [("renders/final.mp4", ".analysis/run-1", "final", 8, ["S001", "S002"])]



def test_dispatch_routes_audio_review_packet_command(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "ai_mv.cli.commands.run_audio_review_packet",
        lambda music_file, output_dir, sections_json, audio_plan_json: calls.append((music_file, output_dir, sections_json, audio_plan_json)) or 0,
    )

    rc = dispatch(
        "audio-review-packet",
        music_file="renders/music.mp3",
        output_dir=".analysis/audio-review",
        sections_json='[{"name":"chorus","start_sec":4.0,"end_sec":12.0}]',
        audio_plan_json='{"genre_description":"idol pop"}',
    )

    assert rc == 0
    assert calls == [(
        "renders/music.mp3",
        ".analysis/audio-review",
        '[{"name":"chorus","start_sec":4.0,"end_sec":12.0}]',
        '{"genre_description":"idol pop"}',
    )]


def test_dispatch_routes_audio_reroll_preflight_command(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "ai_mv.cli.commands.run_audio_reroll_preflight",
        lambda rubric_path, run_id, concept_text, scope: calls.append((rubric_path, run_id, concept_text, scope)) or 0,
    )

    rc = dispatch(
        "audio-reroll-preflight",
        rubric_path=".analysis/audio-review-rubric-reviewed.json",
        run_id="reroll-123",
        concept_text=None,
        scope="run",
    )

    assert rc == 0
    assert calls == [(
        ".analysis/audio-review-rubric-reviewed.json",
        "reroll-123",
        None,
        "run",
    )]


def test_dispatch_routes_audio_reroll_start_command(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "ai_mv.cli.commands.run_audio_reroll_start",
        lambda rubric_path, run_id, concept_text, scope: calls.append((rubric_path, run_id, concept_text, scope)) or 0,
    )

    rc = dispatch(
        "audio-reroll-start",
        rubric_path=".analysis/audio-review-rubric-reviewed.json",
        run_id="reroll-start-123",
        concept_text=None,
        scope="run",
    )

    assert rc == 0
    assert calls == [(
        ".analysis/audio-review-rubric-reviewed.json",
        "reroll-start-123",
        None,
        "run",
    )]


def test_dispatch_routes_audio_review_score_command(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "ai_mv.cli.commands.run_audio_review_score",
        lambda rubric_path, segment_id, scores_json, reason_codes_json, notes, verdict, next_action: calls.append((rubric_path, segment_id, scores_json, reason_codes_json, notes, verdict, next_action)) or 0,
    )

    rc = dispatch(
        "audio-review-score",
        rubric_path=".analysis/audio-review-rubric.json",
        segment_id="first_chorus",
        scores_json='{"hook_memorability":2,"genre_fit":3}',
        reason_codes_json='["weak_hook"]',
        notes="hook is still weak",
        verdict="needs stronger hook",
        next_action="regenerate_audio",
    )

    assert rc == 0
    assert calls == [(
        ".analysis/audio-review-rubric.json",
        "first_chorus",
        '{"hook_memorability":2,"genre_fit":3}',
        '["weak_hook"]',
        "hook is still weak",
        "needs stronger hook",
        "regenerate_audio",
    )]


def test_dispatch_routes_audio_review_batch_score_command(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "ai_mv.cli.commands.run_audio_review_batch_score",
        lambda rubric_path, updates_json, verdict, next_action: calls.append((rubric_path, updates_json, verdict, next_action)) or 0,
    )

    rc = dispatch(
        "audio-review-batch-score",
        rubric_path=".analysis/audio-review-rubric.json",
        updates_json='[{"segment_id":"first_chorus","scores":{"hook_memorability":2},"reason_codes":["weak_hook"],"notes":"hook weak"}]',
        verdict="needs stronger hook",
        next_action="regenerate_audio",
    )

    assert rc == 0
    assert calls == [(
        ".analysis/audio-review-rubric.json",
        '[{"segment_id":"first_chorus","scores":{"hook_memorability":2},"reason_codes":["weak_hook"],"notes":"hook weak"}]',
        "needs stronger hook",
        "regenerate_audio",
    )]


def test_dispatch_routes_audio_review_session_command(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "ai_mv.cli.commands.run_audio_review_session",
        lambda rubric_path, updates_json, verdict, next_action, reroll_mode, run_id, concept_text, scope: calls.append((rubric_path, updates_json, verdict, next_action, reroll_mode, run_id, concept_text, scope)) or 0,
    )

    rc = dispatch(
        "audio-review-session",
        rubric_path=".analysis/audio-review-rubric.json",
        updates_json='[{"segment_id":"first_chorus","scores":{"hook_memorability":2},"reason_codes":["weak_hook"],"notes":"hook weak"}]',
        verdict="needs stronger hook",
        next_action="regenerate_audio",
        reroll_mode="preflight",
        run_id="audio-session-123",
        concept_text=None,
        scope="run",
    )

    assert rc == 0
    assert calls == [(
        ".analysis/audio-review-rubric.json",
        '[{"segment_id":"first_chorus","scores":{"hook_memorability":2},"reason_codes":["weak_hook"],"notes":"hook weak"}]',
        "needs stronger hook",
        "regenerate_audio",
        "preflight",
        "audio-session-123",
        None,
        "run",
    )]


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
    assert calls == [('.analysis/latest-validation', 8, ['S001'])]
