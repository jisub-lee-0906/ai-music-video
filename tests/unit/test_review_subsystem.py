from ai_mv.core.review.models import build_review_report
from ai_mv.core.review.policy import rerender_targets
from ai_mv.core.review.quality_signals import build_quality_signals
from ai_mv.core.review.rerender_policy import rerender_priority_score, rerender_reasons


def test_review_policy_limits_rerender_targets():
    out = rerender_targets(
        ["S001", "S002", "S003"],
        {"S001": True, "S002": False, "S003": False},
        {"S001": False, "S002": True, "S003": False},
        {"review": {"max_rerender_targets": 2}},
    )

    assert out == ["S003", "S001"]


def test_review_policy_prioritizes_higher_severity_reasons_before_limit():
    out = rerender_targets(
        ["S001", "S002", "S003"],
        {"S001": True, "S002": False, "S003": True},
        {"S001": True, "S002": False, "S003": True},
        {"review": {"max_rerender_targets": 2, "max_audio_video_drift_sec": 0.5, "min_stills_coverage_ratio": 0.8, "min_clips_coverage_ratio": 0.8}},
        final_video_exists=False,
        audio_video_drift_sec=1.0,
        coverage={"stills_ratio": 0.5, "clips_ratio": 0.5},
    )

    assert out == ["S002", "S001"]


def test_review_policy_can_use_shot_scores_for_ordering():
    out = rerender_targets(
        ["S001", "S002"],
        {"S001": True, "S002": True},
        {"S001": False, "S002": False},
        {"review": {"max_rerender_targets": 2}},
        shot_scores={"S001": 80.0, "S002": 20.0},
    )

    assert out == ["S002", "S001"]


def test_quality_signals_builds_blocking_and_non_blocking_checks():
    signals = build_quality_signals(
        planned_shot_ids=["S001", "S002"],
        still_status={"S001": True, "S002": False},
        clip_status={"S001": True, "S002": True},
        final_video_exists=True,
        audio_video_drift_sec=0.2,
        config={"review": {"max_audio_video_drift_sec": 0.5}},
    )

    assert signals["still_done"] == 1
    assert signals["clip_done"] == 2
    assert signals["coverage"]["stills_ratio"] == 0.5
    assert signals["coverage"]["clips_ratio"] == 1.0
    assert signals["blocking_checks"]["all_stills_rendered"] is False
    assert signals["blocking_checks"]["audio_video_sync_within_tolerance"] is True
    assert signals["severity"]["drift"] == "low"
    assert signals["severity"]["coverage"] == "medium"
    assert signals["scores"]["overall"] < 100
    assert signals["non_blocking_checks"]["memorable_shot"] is True
    assert signals["non_blocking_checks"]["style_identity"] is True
    assert signals["blocking_checks"]["style_constraints_respected"] is True


def test_rerender_reasons_explain_missing_assets():
    reasons = rerender_reasons(
        ["S001", "S002", "S003"],
        {"S001": True, "S002": False, "S003": False},
        {"S001": False, "S002": True, "S003": False},
    )

    assert reasons["S001"] == ["missing_clip"]
    assert reasons["S002"] == ["missing_still"]
    assert reasons["S003"] == ["missing_still", "missing_clip"]


def test_rerender_reasons_include_quality_failures():
    reasons = rerender_reasons(
        ["S001", "S002", "S003"],
        {"S001": True, "S002": True, "S003": True},
        {"S001": True, "S002": True, "S003": True},
        final_video_exists=False,
        audio_video_drift_sec=0.9,
        coverage={"stills_ratio": 0.5, "clips_ratio": 0.5},
        config={"review": {"max_audio_video_drift_sec": 0.5, "min_stills_coverage_ratio": 0.8, "min_clips_coverage_ratio": 0.8}},
    )

    assert reasons["S001"] == ["missing_final_video", "drift_too_high", "coverage_too_low"]


def test_rerender_priority_score_ranks_quality_failures():
    score = rerender_priority_score(["missing_final_video", "drift_too_high", "coverage_too_low"])
    assert score >= 12


def test_review_models_build_report_from_inputs():
    report = build_review_report(
        planned_shot_ids=["S001"],
        still_results=[{"shot_id": "S001"}],
        clip_results=[{"shot_id": "S001"}],
        still_status={"S001": True},
        clip_status={"S001": True},
        final_video_exists=True,
        rerender_targets=[],
        rerender_reasons={},
        audio_video_drift_sec=0.25,
        config={"review": {"max_audio_video_drift_sec": 0.5}},
    )

    assert report["status"] == "done"
    assert report["completed_counts"]["stills"] == 1
    assert report["completed_counts"]["clips"] == 1
    assert report["audio_video_drift_sec"] == 0.25
    assert report["coverage"]["stills_ratio"] == 1.0
    assert report["rerender_reasons"] == {}


def test_review_models_marks_report_needing_rerender_when_drift_exceeds_tolerance():
    report = build_review_report(
        planned_shot_ids=["S001"],
        still_results=[{"shot_id": "S001"}],
        clip_results=[{"shot_id": "S001"}],
        still_status={"S001": True},
        clip_status={"S001": True},
        final_video_exists=True,
        rerender_targets=["S001"],
        rerender_reasons={"S001": ["drift_too_high"]},
        audio_video_drift_sec=0.75,
        config={"review": {"max_audio_video_drift_sec": 0.5}},
    )

    assert report["status"] == "needs_rerender"
    assert report["blocking_checks"]["audio_video_sync_within_tolerance"] is False
    assert report["rerender_reasons"]["S001"] == ["drift_too_high"]


def test_review_models_include_severity_and_priority():
    report = build_review_report(
        planned_shot_ids=["S001"],
        still_results=[{"shot_id": "S001"}],
        clip_results=[{"shot_id": "S001"}],
        still_status={"S001": True},
        clip_status={"S001": True},
        final_video_exists=False,
        rerender_targets=["S001"],
        rerender_reasons={"S001": ["missing_final_video", "drift_too_high"]},
        audio_video_drift_sec=0.9,
        config={"review": {"max_audio_video_drift_sec": 0.5}},
    )

    assert report["severity"]["drift"] == "high"
    assert report["rerender_priority_scores"]["S001"] >= 9


def test_review_models_include_quality_scores():
    report = build_review_report(
        planned_shot_ids=["S001", "S002"],
        still_results=[{"shot_id": "S001"}, {"shot_id": "S002"}],
        clip_results=[{"shot_id": "S001"}],
        still_status={"S001": True, "S002": True},
        clip_status={"S001": True, "S002": False},
        final_video_exists=True,
        rerender_targets=["S002"],
        rerender_reasons={"S002": ["missing_clip"]},
        audio_video_drift_sec=0.25,
        config={"review": {"max_audio_video_drift_sec": 0.5}},
    )

    assert report["scores"]["overall"] < 100
    assert report["scores"]["shots"]["S001"] > report["scores"]["shots"]["S002"]
    assert report["scores"]["shots"]["S002"] < 100


def test_review_models_respects_min_overall_score_threshold():
    report = build_review_report(
        planned_shot_ids=["S001"],
        still_results=[{"shot_id": "S001"}],
        clip_results=[{"shot_id": "S001"}],
        still_status={"S001": True},
        clip_status={"S001": True},
        final_video_exists=True,
        rerender_targets=[],
        rerender_reasons={},
        audio_video_drift_sec=0.0,
        config={"review": {"min_overall_score": 101}},
    )

    assert report["status"] == "needs_rerender"
    assert report["blocking_checks"]["overall_score_within_threshold"] is False
