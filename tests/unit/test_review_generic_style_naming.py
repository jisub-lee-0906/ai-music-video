from ai_mv.core.review.models import build_review_report


def test_review_report_exposes_generic_style_checks():
    report = build_review_report(
        planned_shot_ids=["S001"],
        still_results=[{"shot_id": "S001"}],
        clip_results=[{"shot_id": "S001"}],
        still_status={"S001": True},
        clip_status={"S001": True},
        final_video_exists=True,
        rerender_targets=[],
        rerender_reasons={},
        audio_video_drift_sec=0.1,
        config={"review": {"max_audio_video_drift_sec": 0.5}},
    )

    assert report["non_blocking_checks"]["style_identity"] is True
    assert report["blocking_checks"]["style_constraints_respected"] is True
