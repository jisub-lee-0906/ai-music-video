from ai_mv.core.review.models import build_review_report
from ai_mv.core.stages.plan_mv import build_plan_preview_payload



def test_plan_preview_exposes_only_style_bible_as_canonical_payload():
    out = build_plan_preview_payload(
        {},
        {
            "concept_text": "Japanese 80s city pop night drive",
            "audio_map": {
                "duration_sec": 8.0,
                "sections": [{"name": "chorus", "start_sec": 0.0, "end_sec": 8.0}],
            },
        },
    )

    assert "style_bible" in out
    assert "citypop_bible" not in out



def test_review_report_exposes_only_generic_style_checks():
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

    assert "style_identity" in report["non_blocking_checks"]
    assert "citypop_identity" not in report["non_blocking_checks"]
    assert "style_constraints_respected" in report["blocking_checks"]
    assert "not_kpop_or_cyberpunk" not in report["blocking_checks"]
