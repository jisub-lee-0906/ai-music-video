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


def test_rerender_reasons_include_explicit_visual_quality_findings():
    reasons = rerender_reasons(
        ["S001", "S002"],
        {"S001": True, "S002": True},
        {"S001": True, "S002": True},
        quality_findings={
            "S002": ["terminal_frame_corruption", "continuity_break", "duplicate_subject"],
        },
    )

    assert reasons["S002"] == ["terminal_frame_corruption", "continuity_break", "duplicate_subject"]
    assert "S001" not in reasons


def test_rerender_priority_score_ranks_quality_failures():
    score = rerender_priority_score(["missing_final_video", "drift_too_high", "coverage_too_low"])
    assert score >= 12


def test_review_models_include_benchmark_dimension_summary():
    report = build_review_report(
        planned_shot_ids=["S001", "S006"],
        still_results=[{"shot_id": "S001"}, {"shot_id": "S006"}],
        clip_results=[{"shot_id": "S001"}, {"shot_id": "S006"}],
        still_status={"S001": True, "S006": True},
        clip_status={"S001": True, "S006": True},
        final_video_exists=True,
        rerender_targets=["S006"],
        rerender_reasons={"S006": ["terminal_frame_corruption", "continuity_break", "duplicate_subject"]},
        audio_video_drift_sec=0.0,
        config={"review": {"max_audio_video_drift_sec": 0.5}},
    )

    benchmark = report["benchmark_dimensions"]
    assert benchmark["temporal_coherence"]["passed"] is False
    assert benchmark["temporal_coherence"]["affected_shots"] == ["S006"]
    assert benchmark["continuity"]["reasons"] == ["continuity_break"]
    assert benchmark["composition"]["reasons"] == ["duplicate_subject"]
    assert benchmark["alignment"]["passed"] is True



def test_review_models_include_review_signal_buckets():
    report = build_review_report(
        planned_shot_ids=["S001", "S006"],
        still_results=[{"shot_id": "S001"}, {"shot_id": "S006"}],
        clip_results=[{"shot_id": "S001"}, {"shot_id": "S006"}],
        still_status={"S001": True, "S006": True},
        clip_status={"S001": True, "S006": True},
        final_video_exists=True,
        rerender_targets=["S006"],
        rerender_reasons={"S006": ["terminal_frame_corruption", "continuity_break", "duplicate_subject"]},
        audio_video_drift_sec=0.0,
        config={"review": {"max_audio_video_drift_sec": 0.5}},
    )

    buckets = report["review_signal_buckets"]
    assert buckets["measurable_deterministic"]["passed"] is True
    assert buckets["measurable_deterministic"]["failed_checks"] == []
    assert buckets["heuristic_proxy"]["passed"] is False
    assert buckets["heuristic_proxy"]["failed_checks"] == ["terminal_frames_clean", "visual_continuity_preserved", "duplicate_subject_absent"]
    assert buckets["model_judged"]["passed"] is False
    assert buckets["model_judged"]["failed_checks"] == ["style_identity", "mood_consistency"]


def test_review_models_include_publishability_summary_levels():
    report = build_review_report(
        planned_shot_ids=["S001", "S006"],
        still_results=[{"shot_id": "S001"}, {"shot_id": "S006"}],
        clip_results=[{"shot_id": "S001"}, {"shot_id": "S006"}],
        still_status={"S001": True, "S006": True},
        clip_status={"S001": True, "S006": True},
        final_video_exists=True,
        rerender_targets=["S006"],
        rerender_reasons={"S006": ["terminal_frame_corruption", "continuity_break", "duplicate_subject"]},
        audio_video_drift_sec=0.0,
        config={"review": {"max_audio_video_drift_sec": 0.5}},
    )

    summary = report["publishability_summary"]
    assert summary["technical_completion"]["passed"] is True
    assert summary["technical_completion"]["blocking_failures"] == []
    assert summary["technical_completion"]["next_action"] == "no_action"
    assert summary["technical_completion"]["rerender_guidance"] == []
    assert summary["technical_completion"]["rerender_bundle"] == {
        "action": "no_action",
        "target_shots": [],
        "reason_codes": [],
    }
    assert summary["technical_completion"]["rerender_prescription"] == {
        "stage_focus": None,
        "workflow_focus": None,
        "prompt_contract_focus": [],
        "fix_strategy": "no_action",
    }
    assert summary["isolated_asset_quality"]["passed"] is False
    assert summary["isolated_asset_quality"]["failed_checks"] == ["terminal_frames_clean", "duplicate_subject_absent", "style_identity"]
    assert summary["isolated_asset_quality"]["next_action"] == "rerender_clips_with_terminal_frame_cleanup"
    assert summary["isolated_asset_quality"]["rerender_guidance"] == [
        "rerender affected clips with cleaner terminal frames and shorter motion range",
        "tighten single-subject framing and remove duplicate subject artifacts",
        "strengthen style-identity prompt constraints and rerender weakest shots",
    ]
    assert summary["isolated_asset_quality"]["rerender_bundle"] == {
        "action": "rerender_clips_with_terminal_frame_cleanup",
        "target_shots": ["S006"],
        "reason_codes": ["duplicate_subject", "terminal_frame_corruption"],
    }
    assert summary["isolated_asset_quality"]["rerender_prescription"] == {
        "stage_focus": "clips",
        "workflow_focus": ["i2v", "ia2v", "flf2v"],
        "prompt_contract_focus": ["clip_prompt_seed", "clip_positive_prompt"],
        "fix_strategy": "shorter_motion_and_clean_terminal_frames",
    }
    assert summary["final_mv_publishability"]["passed"] is False
    assert summary["final_mv_publishability"]["failed_checks"] == ["visual_continuity_preserved", "mood_consistency"]
    assert summary["final_mv_publishability"]["next_action"] == "rerender_continuity_break_shots"
    assert summary["final_mv_publishability"]["rerender_guidance"] == [
        "rerender continuity-break shots and preserve identity across adjacent shots",
        "rerender mood-drift shots to match the song section and neighboring shots",
    ]
    assert summary["final_mv_publishability"]["rerender_bundle"] == {
        "action": "rerender_continuity_break_shots",
        "target_shots": ["S006"],
        "reason_codes": ["continuity_break"],
    }
    assert summary["final_mv_publishability"]["rerender_prescription"] == {
        "stage_focus": "review",
        "workflow_focus": None,
        "prompt_contract_focus": [],
        "fix_strategy": "inspect_review_failures_manually",
    }



def test_review_models_include_shot_level_rerender_plan():
    report = build_review_report(
        planned_shot_ids=["S001", "S002", "S003"],
        still_results=[
            {"shot_id": "S001", "image": "still-1.png"},
            {"shot_id": "S002", "image": "still-2.png"},
            {"shot_id": "S003", "image": "still-3.png"},
            {"shot_id": "S004", "image": "still-4.png"},
        ],
        clip_results=[{"shot_id": "S001"}, {"shot_id": "S002"}, {"shot_id": "S003"}],
        still_status={"S001": True, "S002": True, "S003": True},
        clip_status={"S001": True, "S002": True, "S003": True},
        final_video_exists=True,
        rerender_targets=["S003", "S002", "S001"],
        rerender_reasons={
            "S001": ["panel_layout", "collage_layout"],
            "S002": ["motion_fragile_frame"],
            "S003": ["unrelated_scene_intrusion", "weak_subject_match"],
        },
        audio_video_drift_sec=0.0,
        config={"review": {"max_audio_video_drift_sec": 0.5}},
        shot_plan=[
            {"shot_id": "S001", "render_mode": "i2v"},
            {"shot_id": "S002", "render_mode": "flf2v", "bridge_to_shot_id": "S004"},
            {"shot_id": "S003", "render_mode": "i2v"},
        ],
        render_plan=[
            {"shot_id": "S001", "render_mode": "i2v", "still_prompt_text": "still-1"},
            {"shot_id": "S002", "render_mode": "flf2v", "still_b": "S004", "clip_prompt_seed": "clip-2"},
            {"shot_id": "S003", "render_mode": "i2v", "still_prompt_text": "still-3"},
        ],
        music_file="song.mp3",
    )

    assert [item["shot_id"] for item in report["rerender_plan"]] == ["S003", "S001", "S002"]
    assert report["rerender_plan"][0] == {
        "shot_id": "S003",
        "reason_codes": ["unrelated_scene_intrusion", "weak_subject_match"],
        "priority_score": report["rerender_priority_scores"]["S003"],
        "bucket": "isolated_asset_quality",
        "recommended_action": "rerender_scene_intrusion_shots",
        "rerender_prescription": {
            "stage_focus": "stills",
            "workflow_focus": ["qwen_image"],
            "prompt_contract_focus": ["still_prompt_text"],
            "fix_strategy": "tighten_subject_and_world_anchors",
        },
    }
    assert report["rerender_plan"][1]["recommended_action"] == "rerender_panelized_keyframes"
    assert report["rerender_plan"][1]["bucket"] == "isolated_asset_quality"
    assert report["rerender_plan"][2]["recommended_action"] == "rerender_motion_fragile_shots_with_safer_keyframes"
    assert report["rerender_plan"][2]["bucket"] == "final_mv_publishability"
    assert report["rerender_payload"] == [
        {
            "shot_id": "S003",
            "quality_findings": ["unrelated_scene_intrusion", "weak_subject_match"],
            "rerender_stage": "stills",
            "workflow_focus": ["qwen_image"],
            "prompt_contract_focus": ["still_prompt_text"],
            "recommended_action": "rerender_scene_intrusion_shots",
            "fix_strategy": "tighten_subject_and_world_anchors",
        },
        {
            "shot_id": "S001",
            "quality_findings": ["panel_layout", "collage_layout"],
            "rerender_stage": "stills",
            "workflow_focus": ["qwen_image"],
            "prompt_contract_focus": ["still_prompt_text"],
            "recommended_action": "rerender_panelized_keyframes",
            "fix_strategy": "enforce_single_frame_keyframe_composition",
        },
        {
            "shot_id": "S002",
            "quality_findings": ["motion_fragile_frame"],
            "rerender_stage": "stills_then_clips",
            "workflow_focus": ["qwen_image", "i2v", "flf2v"],
            "prompt_contract_focus": ["still_prompt_text", "clip_prompt_seed", "clip_positive_prompt"],
            "recommended_action": "rerender_motion_fragile_shots_with_safer_keyframes",
            "fix_strategy": "replace_fragile_keyframes_before_clip_rerender",
        },
    ]
    assert report["rerender_execution_payloads"] == [
        {
            "shot_id": "S003",
            "recommended_action": "rerender_scene_intrusion_shots",
            "rerender_stage": "stills",
            "stage_payloads": {
                "stills": {
                    "shot_plan": [{"shot_id": "S003", "render_mode": "i2v"}],
                    "render_plan": [{"shot_id": "S003", "render_mode": "i2v", "still_prompt_text": "still-3"}],
                }
            },
        },
        {
            "shot_id": "S001",
            "recommended_action": "rerender_panelized_keyframes",
            "rerender_stage": "stills",
            "stage_payloads": {
                "stills": {
                    "shot_plan": [{"shot_id": "S001", "render_mode": "i2v"}],
                    "render_plan": [{"shot_id": "S001", "render_mode": "i2v", "still_prompt_text": "still-1"}],
                }
            },
        },
        {
            "shot_id": "S002",
            "recommended_action": "rerender_motion_fragile_shots_with_safer_keyframes",
            "rerender_stage": "stills_then_clips",
            "stage_payloads": {
                "stills": {
                    "shot_plan": [{"shot_id": "S002", "render_mode": "flf2v", "bridge_to_shot_id": "S004"}],
                    "render_plan": [{"shot_id": "S002", "render_mode": "flf2v", "still_b": "S004", "clip_prompt_seed": "clip-2"}],
                },
                "clips": {
                    "shot_plan": [{"shot_id": "S002", "render_mode": "flf2v", "bridge_to_shot_id": "S004"}],
                    "render_plan": [{"shot_id": "S002", "render_mode": "flf2v", "still_b": "S004", "clip_prompt_seed": "clip-2"}],
                    "still_results": [
                        {"shot_id": "S002", "image": "still-2.png"},
                        {"shot_id": "S004", "image": "still-4.png"},
                    ],
                    "music_file": "song.mp3",
                },
            },
        },
    ]



def test_review_models_leave_rerender_plan_empty_when_no_targets():
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
        config={"review": {"max_audio_video_drift_sec": 0.5}},
    )

    assert report["rerender_plan"] == []
    assert report["rerender_payload"] == []
    assert report["rerender_execution_payloads"] == []



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


def test_review_models_fail_visual_continuity_and_corruption_checks_from_rerender_reasons():
    report = build_review_report(
        planned_shot_ids=["S001", "S006"],
        still_results=[{"shot_id": "S001"}, {"shot_id": "S006"}],
        clip_results=[{"shot_id": "S001"}, {"shot_id": "S006"}],
        still_status={"S001": True, "S006": True},
        clip_status={"S001": True, "S006": True},
        final_video_exists=True,
        rerender_targets=["S006"],
        rerender_reasons={"S006": ["terminal_frame_corruption", "continuity_break", "duplicate_subject"]},
        audio_video_drift_sec=0.0,
        config={"review": {"max_audio_video_drift_sec": 0.5}},
    )

    assert report["status"] == "needs_rerender"
    assert report["blocking_checks"]["terminal_frames_clean"] is False
    assert report["blocking_checks"]["visual_continuity_preserved"] is False
    assert report["blocking_checks"]["duplicate_subject_absent"] is False
    assert report["severity"]["visual_quality"] == "high"
    assert report["scores"]["shots"]["S006"] < report["scores"]["shots"]["S001"]



def test_rerender_priority_score_weights_new_publishability_findings():
    score = rerender_priority_score([
        "weak_subject_match",
        "weak_environment_match",
        "motion_fragile_frame",
        "unrelated_scene_intrusion",
    ])

    assert score >= 12



def test_review_models_surface_new_publishability_quality_findings():
    report = build_review_report(
        planned_shot_ids=["S001", "S006"],
        still_results=[{"shot_id": "S001"}, {"shot_id": "S006"}],
        clip_results=[{"shot_id": "S001"}, {"shot_id": "S006"}],
        still_status={"S001": True, "S006": True},
        clip_status={"S001": True, "S006": True},
        final_video_exists=True,
        rerender_targets=["S006"],
        rerender_reasons={
            "S006": [
                "weak_subject_match",
                "weak_environment_match",
                "motion_fragile_frame",
                "unrelated_scene_intrusion",
            ]
        },
        audio_video_drift_sec=0.0,
        config={"review": {"max_audio_video_drift_sec": 0.5}},
    )

    assert report["benchmark_dimensions"]["alignment"]["passed"] is False
    assert report["benchmark_dimensions"]["alignment"]["reasons"] == [
        "weak_subject_match",
        "weak_environment_match",
        "unrelated_scene_intrusion",
    ]
    assert report["benchmark_dimensions"]["motion_quality"]["reasons"] == ["motion_fragile_frame"]
    assert report["benchmark_dimensions"]["faithfulness"]["reasons"] == [
        "weak_subject_match",
        "weak_environment_match",
        "unrelated_scene_intrusion",
    ]
    assert report["review_signal_buckets"]["heuristic_proxy"]["failed_checks"] == [
        "subject_match_preserved",
        "environment_match_preserved",
        "motion_source_safe",
        "scene_intrusion_absent",
    ]
    assert report["publishability_summary"]["isolated_asset_quality"]["failed_checks"] == [
        "style_identity",
        "subject_match_preserved",
        "environment_match_preserved",
        "scene_intrusion_absent",
    ]
    assert report["publishability_summary"]["isolated_asset_quality"]["rerender_bundle"] == {
        "action": "rerender_scene_intrusion_shots",
        "target_shots": ["S006"],
        "reason_codes": [
            "unrelated_scene_intrusion",
            "weak_environment_match",
            "weak_subject_match",
        ],
    }
    assert report["publishability_summary"]["isolated_asset_quality"]["rerender_prescription"] == {
        "stage_focus": "stills",
        "workflow_focus": ["qwen_image"],
        "prompt_contract_focus": ["still_prompt_text"],
        "fix_strategy": "tighten_subject_and_world_anchors",
    }
    assert report["publishability_summary"]["final_mv_publishability"]["failed_checks"] == [
        "mood_consistency",
        "motion_source_safe",
    ]
    assert report["publishability_summary"]["final_mv_publishability"]["rerender_bundle"] == {
        "action": "rerender_motion_fragile_shots_with_safer_keyframes",
        "target_shots": ["S006"],
        "reason_codes": ["motion_fragile_frame"],
    }
    assert report["publishability_summary"]["final_mv_publishability"]["rerender_prescription"] == {
        "stage_focus": "stills_then_clips",
        "workflow_focus": ["qwen_image", "i2v", "flf2v"],
        "prompt_contract_focus": ["still_prompt_text", "clip_prompt_seed", "clip_positive_prompt"],
        "fix_strategy": "replace_fragile_keyframes_before_clip_rerender",
    }



def test_rerender_priority_score_weights_panelized_keyframe_findings():
    score = rerender_priority_score([
        "panel_layout",
        "collage_layout",
        "split_screen",
    ])

    assert score >= 11



def test_review_models_surface_panelized_keyframe_findings():
    report = build_review_report(
        planned_shot_ids=["S001", "S006"],
        still_results=[{"shot_id": "S001"}, {"shot_id": "S006"}],
        clip_results=[{"shot_id": "S001"}, {"shot_id": "S006"}],
        still_status={"S001": True, "S006": True},
        clip_status={"S001": True, "S006": True},
        final_video_exists=True,
        rerender_targets=["S006"],
        rerender_reasons={
            "S006": [
                "panel_layout",
                "collage_layout",
                "split_screen",
            ]
        },
        audio_video_drift_sec=0.0,
        config={"review": {"max_audio_video_drift_sec": 0.5}},
    )

    assert report["benchmark_dimensions"]["composition"]["passed"] is False
    assert report["benchmark_dimensions"]["composition"]["reasons"] == [
        "panel_layout",
        "collage_layout",
        "split_screen",
    ]
    assert report["benchmark_dimensions"]["aesthetics"]["reasons"] == [
        "collage_layout",
        "split_screen",
    ]
    assert report["review_signal_buckets"]["heuristic_proxy"]["failed_checks"] == [
        "panel_layout_absent",
        "collage_layout_absent",
        "split_screen_absent",
    ]
    assert report["publishability_summary"]["isolated_asset_quality"]["failed_checks"] == [
        "panel_layout_absent",
        "collage_layout_absent",
        "split_screen_absent",
    ]
    assert report["publishability_summary"]["isolated_asset_quality"]["next_action"] == "rerender_panelized_keyframes"
    assert report["publishability_summary"]["isolated_asset_quality"]["rerender_bundle"] == {
        "action": "rerender_panelized_keyframes",
        "target_shots": ["S006"],
        "reason_codes": [
            "collage_layout",
            "panel_layout",
            "split_screen",
        ],
    }
    assert report["publishability_summary"]["isolated_asset_quality"]["rerender_prescription"] == {
        "stage_focus": "stills",
        "workflow_focus": ["qwen_image"],
        "prompt_contract_focus": ["still_prompt_text"],
        "fix_strategy": "enforce_single_frame_keyframe_composition",
    }
