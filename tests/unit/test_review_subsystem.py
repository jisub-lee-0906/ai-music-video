from ai_mv.core.review.models import build_rerender_execution_payloads, build_review_report
from ai_mv.core.review.policy import rerender_targets
from ai_mv.core.review.publishability import classify_rerender_target
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
            "S002": [
                "terminal_frame_corruption",
                "continuity_break",
                "duplicate_subject",
                "weak_character_payoff",
                "background_dominant_composition",
            ],
        },
    )

    assert reasons["S002"] == [
        "terminal_frame_corruption",
        "continuity_break",
        "duplicate_subject",
        "weak_character_payoff",
        "background_dominant_composition",
    ]
    assert "S001" not in reasons


def test_rerender_priority_score_ranks_quality_failures():
    score = rerender_priority_score(["missing_final_video", "drift_too_high", "coverage_too_low"])
    assert score >= 12


def test_review_models_include_edit_intent_summary():
    report = build_review_report(
        planned_shot_ids=["S001", "S002"],
        still_results=[{"shot_id": "S001"}, {"shot_id": "S002"}],
        clip_results=[{"shot_id": "S001"}, {"shot_id": "S002"}],
        still_status={"S001": True, "S002": True},
        clip_status={"S001": True, "S002": True},
        final_video_exists=True,
        rerender_targets=[],
        rerender_reasons={},
        audio_video_drift_sec=0.0,
        config={"review": {"max_audio_video_drift_sec": 0.5}},
        edit_intent_by_shot={
            "S001": {
                "edit_priority": "high",
                "section_emphasis": "chorus_push",
                "target_clip_sec": 5.0,
                "transition_in": "accent_in",
                "transition_out": "accent_out",
            },
            "S002": {
                "edit_priority": "medium",
                "section_emphasis": "bridge_contrast",
                "target_clip_sec": 4.0,
                "transition_in": "glide_in",
                "transition_out": "handoff_out",
            },
        },
    )

    assert report["edit_intent_summary"] == {
        "shot_count": 2,
        "high_priority_shots": ["S001"],
        "section_emphasis_counts": {"chorus_push": 1, "bridge_contrast": 1},
    }



def test_review_models_include_mv_intent_checks():
    report = build_review_report(
        planned_shot_ids=["S001", "S002"],
        still_results=[{"shot_id": "S001"}, {"shot_id": "S002"}],
        clip_results=[{"shot_id": "S001"}, {"shot_id": "S002"}],
        still_status={"S001": True, "S002": True},
        clip_status={"S001": True, "S002": True},
        final_video_exists=True,
        rerender_targets=[],
        rerender_reasons={},
        audio_video_drift_sec=0.0,
        config={"review": {"max_audio_video_drift_sec": 0.5}},
        edit_intent_by_shot={
            "S001": {
                "edit_priority": "high",
                "section_emphasis": "chorus_push",
                "target_clip_sec": 5.0,
                "transition_in": "accent_in",
                "transition_out": "accent_out",
            },
            "S002": {
                "edit_priority": "medium",
                "section_emphasis": "bridge_contrast",
                "target_clip_sec": 4.0,
                "transition_in": "glide_in",
                "transition_out": "handoff_out",
            },
        },
    )

    assert report["mv_intent_checks"] == {
        "hook_shot_present": True,
        "section_emphasis_present": True,
        "chorus_emphasis_present": True,
        "bridge_emphasis_present": True,
    }



def test_review_models_include_assembly_quality_summary_from_render_metadata():
    report = build_review_report(
        planned_shot_ids=["S001", "S002", "S003"],
        still_results=[{"shot_id": "S001"}, {"shot_id": "S002"}, {"shot_id": "S003"}],
        clip_results=[{"shot_id": "S001"}, {"shot_id": "S002"}, {"shot_id": "S003"}],
        still_status={"S001": True, "S002": True, "S003": True},
        clip_status={"S001": True, "S002": True, "S003": True},
        final_video_exists=True,
        rerender_targets=[],
        rerender_reasons={},
        audio_video_drift_sec=0.0,
        config={"review": {"max_audio_video_drift_sec": 0.5}},
        edit_intent_by_shot={
            "S001": {
                "edit_priority": "high",
                "section_emphasis": "chorus_push",
                "target_clip_sec": 5.0,
                "transition_in": "accent_in",
                "transition_out": "accent_out",
            },
            "S002": {
                "edit_priority": "medium",
                "section_emphasis": "sequence_support",
                "target_clip_sec": 4.0,
                "transition_in": "cut_in",
                "transition_out": "cut_out",
            },
            "S003": {
                "edit_priority": "medium",
                "section_emphasis": "bridge_contrast",
                "target_clip_sec": 4.0,
                "transition_in": "glide_in",
                "transition_out": "handoff_out",
            },
        },
        render_count_by_shot={"S001": 3, "S002": 1, "S003": 2},
        render_priority_by_shot={"S001": 0.9, "S002": 0.6, "S003": 0.78},
        render_planning_by_shot={
            "S001": {"mode_importance_score": 1.0, "section_emphasis_score": 1.0},
            "S002": {"mode_importance_score": 0.68, "section_emphasis_score": 0.6},
            "S003": {"mode_importance_score": 0.85, "section_emphasis_score": 0.78},
        },
    )

    assert report["assembly_quality_summary"] == {
        "chorus_emphasis_score": 0.9,
        "slideshow_risk_score": 0.13,
        "transition_intentionality_score": 0.67,
        "chorus_emphasis_within_threshold": True,
        "slideshow_risk_within_threshold": True,
    }



def test_review_models_ignore_stale_and_blank_shot_metadata_in_assembly_quality_summary():
    report = build_review_report(
        planned_shot_ids=["S001", "S002", "S003"],
        still_results=[{"shot_id": "S001"}, {"shot_id": "S002"}, {"shot_id": "S003"}],
        clip_results=[{"shot_id": "S001"}, {"shot_id": "S002"}, {"shot_id": "S003"}],
        still_status={"S001": True, "S002": True, "S003": True},
        clip_status={"S001": True, "S002": True, "S003": True},
        final_video_exists=True,
        rerender_targets=[],
        rerender_reasons={},
        audio_video_drift_sec=0.0,
        config={"review": {"max_audio_video_drift_sec": 0.5}},
        edit_intent_by_shot={
            "S001": {"edit_priority": "high", "section_emphasis": "chorus_push", "transition_in": "accent_in", "transition_out": "accent_out"},
            "S002": {"edit_priority": "medium", "section_emphasis": "sequence_support", "transition_in": "cut_in", "transition_out": "cut_out"},
            "S003": {"edit_priority": "medium", "section_emphasis": "bridge_contrast", "transition_in": "glide_in", "transition_out": "handoff_out"},
            "": {"edit_priority": "high", "section_emphasis": "chorus_push", "transition_in": "accent_in", "transition_out": "accent_out"},
            "STALE": {"edit_priority": "high", "section_emphasis": "chorus_push", "transition_in": "accent_in", "transition_out": "accent_out"},
        },
        render_count_by_shot={"S001": 3, "S002": 1, "S003": 2, "": 4, "STALE": 99},
        render_priority_by_shot={"S001": 0.9, "S002": 0.6, "S003": 0.78, "": 1.0, "STALE": 0.0},
        render_planning_by_shot={
            "S001": {"mode_importance_score": 1.0, "section_emphasis_score": 1.0},
            "S002": {"mode_importance_score": 0.68, "section_emphasis_score": 0.6},
            "S003": {"mode_importance_score": 0.85, "section_emphasis_score": 0.78},
            "": {"mode_importance_score": 1.0, "section_emphasis_score": 1.0},
            "STALE": {"mode_importance_score": 0.0, "section_emphasis_score": 0.0},
        },
    )

    assert report["assembly_quality_summary"] == {
        "chorus_emphasis_score": 0.9,
        "slideshow_risk_score": 0.13,
        "transition_intentionality_score": 0.67,
        "chorus_emphasis_within_threshold": True,
        "slideshow_risk_within_threshold": True,
    }



def test_review_models_penalize_repetitive_safe_assembly_patterns_from_cadence_metadata():
    report = build_review_report(
        planned_shot_ids=["S001", "S002", "S003", "S004"],
        still_results=[{"shot_id": "S001"}, {"shot_id": "S002"}, {"shot_id": "S003"}, {"shot_id": "S004"}],
        clip_results=[{"shot_id": "S001"}, {"shot_id": "S002"}, {"shot_id": "S003"}, {"shot_id": "S004"}],
        still_status={"S001": True, "S002": True, "S003": True, "S004": True},
        clip_status={"S001": True, "S002": True, "S003": True, "S004": True},
        final_video_exists=True,
        rerender_targets=[],
        rerender_reasons={},
        audio_video_drift_sec=0.0,
        config={"review": {"max_audio_video_drift_sec": 0.5}},
        edit_intent_by_shot={
            "S001": {"edit_priority": "high", "section_emphasis": "chorus_push", "transition_in": "cut_in", "transition_out": "cut_out"},
            "S002": {"edit_priority": "medium", "section_emphasis": "sequence_support", "transition_in": "cut_in", "transition_out": "cut_out"},
            "S003": {"edit_priority": "medium", "section_emphasis": "sequence_support", "transition_in": "cut_in", "transition_out": "cut_out"},
            "S004": {"edit_priority": "medium", "section_emphasis": "sequence_support", "transition_in": "cut_in", "transition_out": "cut_out"},
        },
        render_count_by_shot={"S001": 1, "S002": 1, "S003": 1, "S004": 1},
        render_priority_by_shot={"S001": 0.7, "S002": 0.7, "S003": 0.7, "S004": 0.7},
        render_planning_by_shot={
            "S001": {"mode_importance_score": 0.8, "section_emphasis_score": 1.0},
            "S002": {"mode_importance_score": 0.7, "section_emphasis_score": 0.6},
            "S003": {"mode_importance_score": 0.7, "section_emphasis_score": 0.6},
            "S004": {"mode_importance_score": 0.7, "section_emphasis_score": 0.6},
        },
        cadence_profile_by_shot={"S001": "support_hold", "S002": "support_hold", "S003": "support_hold", "S004": "support_hold"},
        snap_unit_by_shot={"S001": "free", "S002": "free", "S003": "free", "S004": "free"},
        trimmed_coverage_by_shot={"S001": 4.0, "S002": 4.0, "S003": 4.0, "S004": 4.0},
    )

    assert report["assembly_quality_summary"]["repetitive_edit_risk_score"] == 0.92
    assert report["assembly_quality_summary"]["cadence_variety_score"] == 0.25
    assert report["assembly_quality_summary"]["snap_variety_score"] == 0.33
    assert report["assembly_quality_summary"]["safe_editing_within_threshold"] is False
    assert report["non_blocking_checks"]["mood_consistency"] is False
    assert "safe_editing_within_threshold" in report["publishability_summary"]["final_mv_publishability"]["failed_checks"]
    assert "revise assembly pattern selection and cut density to avoid repetitive safe edits before rerendering clips" in report["publishability_summary"]["final_mv_publishability"]["rerender_guidance"]



def test_review_models_keep_legacy_assembly_summary_when_only_cadence_metadata_is_present():
    report = build_review_report(
        planned_shot_ids=["S001", "S002", "S003"],
        still_results=[{"shot_id": "S001"}, {"shot_id": "S002"}, {"shot_id": "S003"}],
        clip_results=[{"shot_id": "S001"}, {"shot_id": "S002"}, {"shot_id": "S003"}],
        still_status={"S001": True, "S002": True, "S003": True},
        clip_status={"S001": True, "S002": True, "S003": True},
        final_video_exists=True,
        rerender_targets=[],
        rerender_reasons={},
        audio_video_drift_sec=0.0,
        config={"review": {"max_audio_video_drift_sec": 0.5}},
        edit_intent_by_shot={
            "S001": {"edit_priority": "high", "section_emphasis": "chorus_push", "transition_in": "accent_in", "transition_out": "accent_out"},
            "S002": {"edit_priority": "medium", "section_emphasis": "sequence_support", "transition_in": "cut_in", "transition_out": "cut_out"},
            "S003": {"edit_priority": "medium", "section_emphasis": "bridge_contrast", "transition_in": "glide_in", "transition_out": "handoff_out"},
        },
        render_count_by_shot={"S001": 3, "S002": 1, "S003": 2},
        render_priority_by_shot={"S001": 0.9, "S002": 0.6, "S003": 0.78},
        render_planning_by_shot={
            "S001": {"mode_importance_score": 1.0, "section_emphasis_score": 1.0},
            "S002": {"mode_importance_score": 0.68, "section_emphasis_score": 0.6},
            "S003": {"mode_importance_score": 0.85, "section_emphasis_score": 0.78},
        },
        cadence_profile_by_shot={"S001": "hook_dense", "S002": "support_hold", "S003": "bridge_pivot"},
    )

    assert report["assembly_quality_summary"] == {
        "chorus_emphasis_score": 0.9,
        "slideshow_risk_score": 0.13,
        "transition_intentionality_score": 0.67,
        "chorus_emphasis_within_threshold": True,
        "slideshow_risk_within_threshold": True,
    }



def test_review_models_reward_varied_cadence_and_snap_patterns_in_assembly_quality_summary():
    report = build_review_report(
        planned_shot_ids=["S001", "S002", "S003", "S004"],
        still_results=[{"shot_id": "S001"}, {"shot_id": "S002"}, {"shot_id": "S003"}, {"shot_id": "S004"}],
        clip_results=[{"shot_id": "S001"}, {"shot_id": "S002"}, {"shot_id": "S003"}, {"shot_id": "S004"}],
        still_status={"S001": True, "S002": True, "S003": True, "S004": True},
        clip_status={"S001": True, "S002": True, "S003": True, "S004": True},
        final_video_exists=True,
        rerender_targets=[],
        rerender_reasons={},
        audio_video_drift_sec=0.0,
        config={"review": {"max_audio_video_drift_sec": 0.5}},
        edit_intent_by_shot={
            "S001": {"edit_priority": "high", "section_emphasis": "chorus_push", "transition_in": "accent_in", "transition_out": "accent_out"},
            "S002": {"edit_priority": "medium", "section_emphasis": "sequence_support", "transition_in": "hold_in", "transition_out": "cut_out"},
            "S003": {"edit_priority": "medium", "section_emphasis": "bridge_contrast", "transition_in": "glide_in", "transition_out": "handoff_out"},
            "S004": {"edit_priority": "medium", "section_emphasis": "release_fade", "transition_in": "hold_in", "transition_out": "fade_out"},
        },
        render_count_by_shot={"S001": 3, "S002": 1, "S003": 2, "S004": 2},
        render_priority_by_shot={"S001": 0.9, "S002": 0.62, "S003": 0.78, "S004": 0.74},
        render_planning_by_shot={
            "S001": {"mode_importance_score": 1.0, "section_emphasis_score": 1.0},
            "S002": {"mode_importance_score": 0.68, "section_emphasis_score": 0.6},
            "S003": {"mode_importance_score": 0.85, "section_emphasis_score": 0.78},
            "S004": {"mode_importance_score": 0.82, "section_emphasis_score": 0.72},
        },
        cadence_profile_by_shot={"S001": "hook_dense", "S002": "support_hold", "S003": "bridge_pivot", "S004": "release_tail"},
        snap_unit_by_shot={"S001": "bar", "S002": "beat", "S003": "free", "S004": "bar"},
        trimmed_coverage_by_shot={"S001": 2.0, "S002": 4.2, "S003": 2.8, "S004": 3.6},
    )

    assert report["assembly_quality_summary"]["repetitive_edit_risk_score"] == 0.23
    assert report["assembly_quality_summary"]["cadence_variety_score"] == 1.0
    assert report["assembly_quality_summary"]["snap_variety_score"] == 1.0
    assert report["assembly_quality_summary"]["safe_editing_within_threshold"] is True
    assert report["non_blocking_checks"]["mood_consistency"] is True



def test_review_models_include_assembly_revision_summary():
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
        assembly_revision={
            "action": "revise_assembly_weights_before_clip_rerender",
            "target": "assembly",
            "final_video": "final.mp4",
            "music_file": "song.mp3",
        },
    )

    assert report["assembly_revision_summary"] == {
        "present": True,
        "action": "revise_assembly_weights_before_clip_rerender",
        "target": "assembly",
        "final_video": "final.mp4",
        "music_file": "song.mp3",
        "target_shots": [],
        "target_material_ids": [],
        "target_section_ids": [],
    }



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
        "target_material_ids": [],
        "target_section_ids": [],
        "reason_codes": ["duplicate_subject", "terminal_frame_corruption"],
    }
    assert summary["isolated_asset_quality"]["rerender_prescription"] == {
        "stage_focus": "clips",
        "workflow_focus": ["ia2v"],
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
        "target_material_ids": [],
        "target_section_ids": [],
        "reason_codes": ["continuity_break"],
    }
    assert summary["final_mv_publishability"]["rerender_prescription"] == {
        "stage_focus": "review",
        "workflow_focus": None,
        "prompt_contract_focus": [],
        "fix_strategy": "inspect_review_failures_manually",
    }



def test_review_models_emit_blueprint_aligned_final_review_summary_scores_and_tier():
    report = build_review_report(
        planned_shot_ids=["S001", "S002"],
        still_results=[{"shot_id": "S001"}, {"shot_id": "S002"}],
        clip_results=[{"shot_id": "S001"}, {"shot_id": "S002"}],
        still_status={"S001": True, "S002": True},
        clip_status={"S001": True, "S002": True},
        final_video_exists=True,
        rerender_targets=[],
        rerender_reasons={},
        audio_video_drift_sec=0.0,
        config={"review": {"max_audio_video_drift_sec": 0.5}},
        assembly_quality_summary={
            "chorus_emphasis_score": 0.82,
            "transition_intentionality_score": 0.8,
            "slideshow_risk_score": 0.12,
            "chorus_emphasis_within_threshold": True,
            "slideshow_risk_within_threshold": True,
        },
    )

    assert report["overall_status"] == "pass"
    assert report["publishability_tier"] == "publishable"
    assert report["recommended_next_action"] == "publish"
    assert report["scores"]["overall"] == 100.0
    assert report["scores"]["technical_completion"] == 100.0
    assert report["scores"]["material_quality"] == 100.0
    assert report["scores"]["final_mv_quality"] == 92.6
    assert report["scores"]["shots"] == {"S001": 100.0, "S002": 100.0}



def test_review_models_downgrade_final_review_summary_when_blocking_failures_exist():
    report = build_review_report(
        planned_shot_ids=["S001", "S002"],
        still_results=[{"shot_id": "S001"}, {"shot_id": "S002"}],
        clip_results=[{"shot_id": "S001"}],
        still_status={"S001": True, "S002": True},
        clip_status={"S001": True, "S002": False},
        final_video_exists=True,
        rerender_targets=["S002"],
        rerender_reasons={"S002": ["missing_clip"]},
        audio_video_drift_sec=0.0,
        config={"review": {"max_audio_video_drift_sec": 0.5}},
        assembly_quality_summary={
            "chorus_emphasis_score": 0.82,
            "transition_intentionality_score": 0.8,
            "slideshow_risk_score": 0.12,
            "chorus_emphasis_within_threshold": True,
            "slideshow_risk_within_threshold": True,
        },
    )

    assert report["overall_status"] == "review_required"
    assert report["publishability_tier"] == "draft_only"
    assert report["recommended_next_action"] == "rerender_missing_clips"
    assert report["scores"]["technical_completion"] == 66.67
    assert report["scores"]["material_quality"] == 100.0
    assert report["scores"]["final_mv_quality"] == 85.93



def test_review_models_treat_assembly_publishability_failures_as_mood_consistency_failures():
    report = build_review_report(
        planned_shot_ids=["S001", "S002"],
        still_results=[{"shot_id": "S001"}, {"shot_id": "S002"}],
        clip_results=[{"shot_id": "S001"}, {"shot_id": "S002"}],
        still_status={"S001": True, "S002": True},
        clip_status={"S001": True, "S002": True},
        final_video_exists=True,
        rerender_targets=[],
        rerender_reasons={},
        audio_video_drift_sec=0.0,
        config={"review": {"max_audio_video_drift_sec": 0.5}},
        assembly_quality_summary={
            "chorus_emphasis_score": 0.24,
            "transition_intentionality_score": 0.18,
            "slideshow_risk_score": 0.72,
            "chorus_emphasis_within_threshold": False,
            "slideshow_risk_within_threshold": False,
        },
    )

    assert report["non_blocking_checks"]["mood_consistency"] is False
    assert report["review_signal_buckets"]["model_judged"]["failed_checks"] == ["mood_consistency"]
    assert report["publishability_summary"]["final_mv_publishability"]["failed_checks"] == [
        "mood_consistency",
        "chorus_emphasis_within_threshold",
        "slideshow_risk_within_threshold",
    ]



def test_review_models_build_rerender_plan_payload_and_execution_payloads():
    report = build_review_report(
        planned_shot_ids=["S001", "S002", "S003"],
        still_results=[
            {"shot_id": "S001", "image": "still-1.png"},
            {"shot_id": "S002", "image": "still-2.png"},
            {"shot_id": "S003", "image": "still-3.png"},
            {"shot_id": "S004", "image": "still-4.png"},
        ],
        clip_results=[
            {"shot_id": "S001", "video": "clip-1.mp4"},
            {"shot_id": "S002", "video": "clip-2.mp4"},
            {"shot_id": "S003", "video": "clip-3.mp4"},
        ],
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
            {"shot_id": "S001", "material_id": "MAT_001", "render_mode": "ia2v"},
            {"shot_id": "S002", "material_id": "MAT_002", "render_mode": "ia2v"},
            {"shot_id": "S003", "material_id": "MAT_003", "render_mode": "ia2v"},
        ],
        material_plan=[
            {"material_id": "MAT_001", "section_id": "SEC_001"},
            {"material_id": "MAT_002", "section_id": "SEC_002"},
            {"material_id": "MAT_003", "section_id": "SEC_003"},
        ],
        render_plan=[
            {"shot_id": "S001", "material_id": "MAT_001", "render_mode": "ia2v", "still_prompt_text": "still-1"},
            {"shot_id": "S002", "material_id": "MAT_002", "render_mode": "ia2v", "clip_prompt_seed": "clip-2"},
            {"shot_id": "S003", "material_id": "MAT_003", "render_mode": "ia2v", "still_prompt_text": "still-3"},
        ],
        style_bible={"style": "synthwave"},
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
            "workflow_focus": ["flux2_image"],
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
            "workflow_focus": ["flux2_image"],
            "prompt_contract_focus": ["still_prompt_text"],
            "recommended_action": "rerender_scene_intrusion_shots",
            "fix_strategy": "tighten_subject_and_world_anchors",
        },
        {
            "shot_id": "S001",
            "quality_findings": ["panel_layout", "collage_layout"],
            "rerender_stage": "stills",
            "workflow_focus": ["flux2_image"],
            "prompt_contract_focus": ["still_prompt_text"],
            "recommended_action": "rerender_panelized_keyframes",
            "fix_strategy": "enforce_single_frame_keyframe_composition",
        },
        {
            "shot_id": "S002",
            "quality_findings": ["motion_fragile_frame"],
            "rerender_stage": "stills_then_clips",
            "workflow_focus": ["flux2_image", "ia2v"],
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
            "workflow_focus": ["flux2_image"],
            "prompt_contract_focus": ["still_prompt_text"],
            "fix_strategy": "tighten_subject_and_world_anchors",
            "stage_payloads": {
                "stills": {
                    "shot_plan": [{"shot_id": "S003", "material_id": "MAT_003", "render_mode": "ia2v"}],
                    "material_plan": [{"material_id": "MAT_003", "section_id": "SEC_003"}],
                    "render_plan": [{"shot_id": "S003", "material_id": "MAT_003", "render_mode": "ia2v", "still_prompt_text": "still-3"}],
                    "style_bible": {"style": "synthwave"},
                }
            },
        },
        {
            "shot_id": "S001",
            "recommended_action": "rerender_panelized_keyframes",
            "rerender_stage": "stills",
            "workflow_focus": ["flux2_image"],
            "prompt_contract_focus": ["still_prompt_text"],
            "fix_strategy": "enforce_single_frame_keyframe_composition",
            "stage_payloads": {
                "stills": {
                    "shot_plan": [{"shot_id": "S001", "material_id": "MAT_001", "render_mode": "ia2v"}],
                    "material_plan": [{"material_id": "MAT_001", "section_id": "SEC_001"}],
                    "render_plan": [{"shot_id": "S001", "material_id": "MAT_001", "render_mode": "ia2v", "still_prompt_text": "still-1"}],
                    "style_bible": {"style": "synthwave"},
                }
            },
        },
        {
            "shot_id": "S002",
            "recommended_action": "rerender_motion_fragile_shots_with_safer_keyframes",
            "rerender_stage": "stills_then_clips",
            "workflow_focus": ["flux2_image", "ia2v"],
            "prompt_contract_focus": ["still_prompt_text", "clip_prompt_seed", "clip_positive_prompt"],
            "fix_strategy": "replace_fragile_keyframes_before_clip_rerender",
            "stage_payloads": {
                "stills": {
                    "shot_plan": [{"shot_id": "S002", "material_id": "MAT_002", "render_mode": "ia2v"}],
                    "material_plan": [{"material_id": "MAT_002", "section_id": "SEC_002"}],
                    "render_plan": [{"shot_id": "S002", "material_id": "MAT_002", "render_mode": "ia2v", "clip_prompt_seed": "clip-2"}],
                    "style_bible": {"style": "synthwave"},
                },
                "clips": {
                    "shot_plan": [{"shot_id": "S002", "material_id": "MAT_002", "render_mode": "ia2v"}],
                    "render_plan": [{"shot_id": "S002", "material_id": "MAT_002", "render_mode": "ia2v", "clip_prompt_seed": "clip-2"}],
                    "still_results": [
                        {"shot_id": "S002", "image": "still-2.png", "material_id": "MAT_002"},
                    ],
                    "music_file": "song.mp3",
                },
            },
        },
    ]



def test_review_models_build_rerender_execution_payloads_falls_back_to_shot_material_id_when_render_row_omits_it():
    payloads = build_rerender_execution_payloads(
        rerender_payload=[{"shot_id": "S001", "rerender_stage": "stills", "recommended_action": "rerender_panelized_keyframes"}],
        shot_plan=[{"shot_id": "S001", "material_id": "MAT_001", "render_mode": "ia2v"}],
        material_plan=[{"material_id": "MAT_001", "section_id": "SEC_001"}],
        render_plan=[{"shot_id": "S001", "render_mode": "ia2v", "still_prompt_text": "still-1"}],
        still_results=[],
        style_bible={"style": "synthwave"},
        music_file="song.mp3",
    )

    assert payloads[0]["stage_payloads"]["stills"]["render_plan"][0]["material_id"] == "MAT_001"
    assert payloads[0]["stage_payloads"]["stills"]["material_plan"] == [{"material_id": "MAT_001", "section_id": "SEC_001"}]



def test_review_models_build_rerender_execution_payloads_normalizes_blank_render_material_id():
    payloads = build_rerender_execution_payloads(
        rerender_payload=[{"shot_id": "S001", "rerender_stage": "stills", "recommended_action": "rerender_panelized_keyframes"}],
        shot_plan=[{"shot_id": "S001", "material_id": "MAT_001", "render_mode": "ia2v"}],
        material_plan=[{"material_id": "MAT_001", "section_id": "SEC_001"}],
        render_plan=[{"shot_id": "S001", "material_id": "", "render_mode": "ia2v", "still_prompt_text": "still-1"}],
        still_results=[],
        style_bible={"style": "synthwave"},
        music_file="song.mp3",
    )

    assert payloads[0]["stage_payloads"]["stills"]["render_plan"][0]["material_id"] == "MAT_001"



def test_review_models_build_rerender_execution_payloads_normalizes_blank_clips_render_material_id():
    payloads = build_rerender_execution_payloads(
        rerender_payload=[{"shot_id": "S001", "rerender_stage": "clips", "recommended_action": "rerender_motion_fragile_shots_with_safer_keyframes"}],
        shot_plan=[{"shot_id": "S001", "material_id": "MAT_001", "render_mode": "ia2v"}],
        material_plan=[{"material_id": "MAT_001", "section_id": "SEC_001"}],
        render_plan=[{"shot_id": "S001", "material_id": "", "render_mode": "ia2v", "clip_prompt_seed": "clip-1"}],
        still_results=[{"shot_id": "S001", "material_id": "MAT_001", "image": "still-1.png"}],
        style_bible={"style": "synthwave"},
        music_file="song.mp3",
    )

    assert payloads[0]["stage_payloads"]["clips"]["render_plan"][0]["material_id"] == "MAT_001"



def test_classify_rerender_target_uses_world_anchor_fix_strategy_for_environment_match():
    classification = classify_rerender_target(["weak_environment_match"])

    assert classification == {
        "bucket": "isolated_asset_quality",
        "recommended_action": "rerender_weak_shots_with_prompt_tightening",
        "rerender_prescription": {
            "stage_focus": "stills",
            "workflow_focus": ["flux2_image"],
            "prompt_contract_focus": ["still_prompt_text"],
            "fix_strategy": "tighten_subject_and_world_anchors",
        },
    }



def test_classify_rerender_target_uses_subject_identity_fix_strategy_for_subject_match():
    classification = classify_rerender_target(["weak_subject_match"])

    assert classification == {
        "bucket": "isolated_asset_quality",
        "recommended_action": "rerender_weak_shots_with_prompt_tightening",
        "rerender_prescription": {
            "stage_focus": "stills",
            "workflow_focus": ["flux2_image"],
            "prompt_contract_focus": ["still_prompt_text"],
            "fix_strategy": "tighten_subject_identity_anchors",
        },
    }



def test_classify_rerender_target_uses_identity_continuity_fix_strategy_for_identity_drift():
    classification = classify_rerender_target(["identity_drift"])

    assert classification == {
        "bucket": "isolated_asset_quality",
        "recommended_action": "rerender_weak_shots_with_prompt_tightening",
        "rerender_prescription": {
            "stage_focus": "stills_then_clips",
            "workflow_focus": ["flux2_image", "ia2v"],
            "prompt_contract_focus": ["still_prompt_text", "clip_prompt_seed", "clip_positive_prompt"],
            "fix_strategy": "tighten_identity_continuity_anchors",
        },
    }



def test_classify_rerender_target_uses_composite_continuity_policy_for_identity_drift_and_continuity_break():
    classification = classify_rerender_target(["continuity_break", "identity_drift"])

    assert classification == {
        "bucket": "final_mv_publishability",
        "recommended_action": "rerender_continuity_break_shots",
        "rerender_prescription": {
            "stage_focus": "stills_then_clips",
            "workflow_focus": ["flux2_image", "ia2v"],
            "prompt_contract_focus": ["still_prompt_text", "clip_prompt_seed", "clip_positive_prompt"],
            "fix_strategy": "tighten_identity_continuity_anchors",
        },
    }



def test_classify_rerender_target_uses_character_payoff_fix_strategy_for_background_dominant_safe_frames():
    classification = classify_rerender_target(["weak_character_payoff", "background_dominant_composition"])

    assert classification == {
        "bucket": "final_mv_publishability",
        "recommended_action": "rerender_character_payoff_shots",
        "rerender_prescription": {
            "stage_focus": "stills_then_clips",
            "workflow_focus": ["flux2_image", "ia2v"],
            "prompt_contract_focus": ["still_prompt_text", "clip_prompt_seed", "clip_positive_prompt"],
            "fix_strategy": "strengthen_character_payoff_and_subject_scale",
        },
    }



def test_review_models_route_manual_payoff_findings_to_final_mv_publishability_summary():
    report = build_review_report(
        planned_shot_ids=["S001", "S002"],
        still_results=[{"shot_id": "S001"}, {"shot_id": "S002"}],
        clip_results=[{"shot_id": "S001"}, {"shot_id": "S002"}],
        still_status={"S001": True, "S002": True},
        clip_status={"S001": True, "S002": True},
        final_video_exists=True,
        rerender_targets=["S001"],
        rerender_reasons={"S001": ["weak_character_payoff", "background_dominant_composition"]},
        audio_video_drift_sec=0.0,
        config={"review": {"max_audio_video_drift_sec": 0.5}},
        assembly_quality_summary={
            "chorus_emphasis_score": 0.84,
            "slideshow_risk_score": 0.22,
            "transition_intentionality_score": 0.74,
            "chorus_emphasis_within_threshold": True,
            "slideshow_risk_within_threshold": True,
        },
    )

    assert report["blocking_checks"]["character_payoff_present"] is False
    assert report["blocking_checks"]["background_dominance_within_threshold"] is False
    assert report["review_signal_buckets"]["heuristic_proxy"]["failed_checks"] == [
        "character_payoff_present",
        "background_dominance_within_threshold",
    ]
    assert report["publishability_summary"]["isolated_asset_quality"]["passed"] is True
    assert report["publishability_summary"]["isolated_asset_quality"]["next_action"] == "no_action"
    assert report["publishability_summary"]["final_mv_publishability"]["failed_checks"] == [
        "mood_consistency",
        "character_payoff_present",
        "background_dominance_within_threshold",
    ]
    assert report["publishability_summary"]["final_mv_publishability"]["next_action"] == "rerender_character_payoff_shots"
    assert report["recommended_next_action"] == "rerender_character_payoff_shots"
    assert report["publishability_summary"]["final_mv_publishability"]["rerender_bundle"] == {
        "action": "rerender_character_payoff_shots",
        "target_shots": ["S001"],
        "target_material_ids": [],
        "target_section_ids": [],
        "reason_codes": ["background_dominant_composition", "weak_character_payoff"],
    }
    assert report["publishability_summary"]["final_mv_publishability"]["rerender_prescription"] == {
        "stage_focus": "stills_then_clips",
        "workflow_focus": ["flux2_image", "ia2v"],
        "prompt_contract_focus": ["still_prompt_text", "clip_prompt_seed", "clip_positive_prompt"],
        "fix_strategy": "strengthen_character_payoff_and_subject_scale",
    }



def test_review_models_route_single_manual_payoff_findings_to_character_payoff_rerender():
    weak_payoff = classify_rerender_target(["weak_character_payoff"])
    background_dominant = classify_rerender_target(["background_dominant_composition"])

    assert weak_payoff["recommended_action"] == "rerender_character_payoff_shots"
    assert background_dominant["recommended_action"] == "rerender_character_payoff_shots"



def test_review_models_preserve_prompt_repair_contract_in_character_payoff_execution_payloads():
    report = build_review_report(
        planned_shot_ids=["S006"],
        still_results=[{"shot_id": "S006", "image": "still.png", "material_id": "MAT_006", "section_id": "SEC_006"}],
        clip_results=[{"shot_id": "S006", "video": "clip.mp4", "material_id": "MAT_006", "section_id": "SEC_006"}],
        still_status={"S006": True},
        clip_status={"S006": True},
        final_video_exists=True,
        rerender_targets=["S006"],
        rerender_reasons={"S006": ["weak_character_payoff", "background_dominant_composition"]},
        audio_video_drift_sec=0.0,
        config={"review": {"max_audio_video_drift_sec": 0.5}},
        shot_plan=[{"shot_id": "S006", "material_id": "MAT_006", "section_id": "SEC_006", "render_mode": "ia2v"}],
        material_plan=[{"material_id": "MAT_006", "section_id": "SEC_006"}],
        render_plan=[
            {
                "shot_id": "S006",
                "material_id": "MAT_006",
                "section_id": "SEC_006",
                "render_mode": "ia2v",
                "still_prompt_text": "wide neon bridge at dusk",
                "clip_prompt_seed": "slow bridge walk, dreamy city lights",
                "clip_positive_prompt": "slow bridge walk, dreamy city lights, cinematic atmosphere",
            }
        ],
        music_file="song.mp3",
        final_video_path="final.mp4",
        assembly_quality_summary={
            "chorus_emphasis_score": 0.84,
            "slideshow_risk_score": 0.22,
            "transition_intentionality_score": 0.74,
            "chorus_emphasis_within_threshold": True,
            "slideshow_risk_within_threshold": True,
        },
    )

    assert report["rerender_execution_payloads"] == [
        {
            "shot_id": "S006",
            "recommended_action": "rerender_character_payoff_shots",
            "rerender_stage": "stills_then_clips",
            "workflow_focus": ["flux2_image", "ia2v"],
            "fix_strategy": "strengthen_character_payoff_and_subject_scale",
            "prompt_contract_focus": ["still_prompt_text", "clip_prompt_seed", "clip_positive_prompt"],
            "stage_payloads": {
                "stills": {
                    "shot_plan": [{"shot_id": "S006", "material_id": "MAT_006", "section_id": "SEC_006", "render_mode": "ia2v"}],
                    "material_plan": [{"material_id": "MAT_006", "section_id": "SEC_006"}],
                    "render_plan": [
                        {
                            "shot_id": "S006",
                            "material_id": "MAT_006",
                            "section_id": "SEC_006",
                            "render_mode": "ia2v",
                            "still_prompt_text": "wide neon bridge at dusk",
                            "clip_prompt_seed": "slow bridge walk, dreamy city lights",
                            "clip_positive_prompt": "slow bridge walk, dreamy city lights, cinematic atmosphere",
                        }
                    ],
                    "style_bible": {},
                },
                "clips": {
                    "shot_plan": [{"shot_id": "S006", "material_id": "MAT_006", "section_id": "SEC_006", "render_mode": "ia2v"}],
                    "render_plan": [
                        {
                            "shot_id": "S006",
                            "material_id": "MAT_006",
                            "section_id": "SEC_006",
                            "render_mode": "ia2v",
                            "still_prompt_text": "wide neon bridge at dusk",
                            "clip_prompt_seed": "slow bridge walk, dreamy city lights",
                            "clip_positive_prompt": "slow bridge walk, dreamy city lights, cinematic atmosphere",
                        }
                    ],
                    "still_results": [{"shot_id": "S006", "image": "still.png", "material_id": "MAT_006", "section_id": "SEC_006"}],
                    "music_file": "song.mp3",
                },
            },
        }
    ]



def test_review_models_lower_final_mv_quality_score_for_manual_payoff_failures():
    baseline = build_review_report(
        planned_shot_ids=["S001", "S002"],
        still_results=[{"shot_id": "S001"}, {"shot_id": "S002"}],
        clip_results=[{"shot_id": "S001"}, {"shot_id": "S002"}],
        still_status={"S001": True, "S002": True},
        clip_status={"S001": True, "S002": True},
        final_video_exists=True,
        rerender_targets=[],
        rerender_reasons={},
        audio_video_drift_sec=0.0,
        config={"review": {"max_audio_video_drift_sec": 0.5}},
        assembly_quality_summary={
            "chorus_emphasis_score": 0.84,
            "slideshow_risk_score": 0.22,
            "transition_intentionality_score": 0.74,
            "chorus_emphasis_within_threshold": True,
            "slideshow_risk_within_threshold": True,
        },
    )
    degraded = build_review_report(
        planned_shot_ids=["S001", "S002"],
        still_results=[{"shot_id": "S001"}, {"shot_id": "S002"}],
        clip_results=[{"shot_id": "S001"}, {"shot_id": "S002"}],
        still_status={"S001": True, "S002": True},
        clip_status={"S001": True, "S002": True},
        final_video_exists=True,
        rerender_targets=["S001"],
        rerender_reasons={"S001": ["weak_character_payoff", "background_dominant_composition"]},
        audio_video_drift_sec=0.0,
        config={"review": {"max_audio_video_drift_sec": 0.5}},
        assembly_quality_summary={
            "chorus_emphasis_score": 0.84,
            "slideshow_risk_score": 0.22,
            "transition_intentionality_score": 0.74,
            "chorus_emphasis_within_threshold": True,
            "slideshow_risk_within_threshold": True,
        },
    )

    assert degraded["scores"]["final_mv_quality"] < baseline["scores"]["final_mv_quality"]
    assert degraded["scores"]["final_mv_quality"] <= 85.0



def test_review_models_backfill_rerender_bundle_provenance_from_legacy_manifest_shot_context():
    report = build_review_report(
        planned_shot_ids=["S004", "S006"],
        still_results=[{"shot_id": "S004"}, {"shot_id": "S006"}],
        clip_results=[{"shot_id": "S004"}, {"shot_id": "S006"}],
        still_status={"S004": True, "S006": True},
        clip_status={"S004": True, "S006": True},
        final_video_exists=True,
        rerender_targets=["S004", "S006"],
        rerender_reasons={
            "S004": ["weak_character_payoff", "background_dominant_composition"],
            "S006": ["weak_character_payoff", "background_dominant_composition"],
        },
        audio_video_drift_sec=0.0,
        config={"review": {"max_audio_video_drift_sec": 0.5}},
        shot_plan=[
            {"shot_id": "S004", "section_name": "Verse 2->Bridge", "source_section_index": 5},
            {"shot_id": "S006", "section_name": "Outro", "source_section_index": 8},
        ],
        render_plan=[{"shot_id": "S004"}, {"shot_id": "S006"}],
        assembly_quality_summary={
            "chorus_emphasis_score": 0.84,
            "slideshow_risk_score": 0.22,
            "transition_intentionality_score": 0.74,
            "chorus_emphasis_within_threshold": True,
            "slideshow_risk_within_threshold": True,
        },
    )

    assert report["publishability_summary"]["final_mv_publishability"]["rerender_bundle"] == {
        "action": "rerender_character_payoff_shots",
        "target_shots": ["S004", "S006"],
        "target_material_ids": ["MAT_001", "MAT_002"],
        "target_section_ids": ["SEC_001", "SEC_002"],
        "reason_codes": ["background_dominant_composition", "weak_character_payoff"],
    }



def test_review_models_prefer_explicit_rerender_bundle_provenance_over_legacy_manifest_backfill():
    report = build_review_report(
        planned_shot_ids=["S004"],
        still_results=[{"shot_id": "S004", "material_id": "MAT_777", "section_id": "SEC_777"}],
        clip_results=[{"shot_id": "S004"}],
        still_status={"S004": True},
        clip_status={"S004": True},
        final_video_exists=True,
        rerender_targets=["S004"],
        rerender_reasons={"S004": ["weak_character_payoff", "background_dominant_composition"]},
        audio_video_drift_sec=0.0,
        config={"review": {"max_audio_video_drift_sec": 0.5}},
        shot_plan=[{"shot_id": "S004", "section_name": "Verse 2->Bridge", "source_section_index": 5}],
        render_plan=[{"shot_id": "S004"}],
        assembly_quality_summary={
            "chorus_emphasis_score": 0.84,
            "slideshow_risk_score": 0.22,
            "transition_intentionality_score": 0.74,
            "chorus_emphasis_within_threshold": True,
            "slideshow_risk_within_threshold": True,
        },
    )

    assert report["publishability_summary"]["final_mv_publishability"]["rerender_bundle"] == {
        "action": "rerender_character_payoff_shots",
        "target_shots": ["S004"],
        "target_material_ids": ["MAT_777"],
        "target_section_ids": ["SEC_777"],
        "reason_codes": ["background_dominant_composition", "weak_character_payoff"],
    }



def test_review_models_preserve_sparse_live_manifest_order_when_backfilling_rerender_bundle_provenance():
    shot_plan = [
        {"shot_id": "S001", "section_name": "Intro->Verse 1", "source_section_index": 1},
        {"shot_id": "S002", "section_name": "Pre-Chorus", "source_section_index": 3},
        {"shot_id": "S003", "section_name": "Chorus", "source_section_index": 4},
        {"shot_id": "S004", "section_name": "Verse 2->Bridge", "source_section_index": 5},
        {"shot_id": "S005", "section_name": "Final Chorus", "source_section_index": 7},
        {"shot_id": "S006", "section_name": "Outro", "source_section_index": 8},
    ]
    report = build_review_report(
        planned_shot_ids=[row["shot_id"] for row in shot_plan],
        still_results=[{"shot_id": row["shot_id"]} for row in shot_plan],
        clip_results=[{"shot_id": row["shot_id"]} for row in shot_plan],
        still_status={row["shot_id"]: True for row in shot_plan},
        clip_status={row["shot_id"]: True for row in shot_plan},
        final_video_exists=True,
        rerender_targets=["S001", "S004", "S006"],
        rerender_reasons={
            "S001": ["weak_character_payoff", "background_dominant_composition"],
            "S004": ["weak_character_payoff", "background_dominant_composition"],
            "S006": ["weak_character_payoff", "background_dominant_composition"],
        },
        audio_video_drift_sec=0.0,
        config={"review": {"max_audio_video_drift_sec": 0.5}},
        shot_plan=shot_plan,
        render_plan=[{"shot_id": row["shot_id"]} for row in shot_plan],
        assembly_quality_summary={
            "chorus_emphasis_score": 0.84,
            "slideshow_risk_score": 0.22,
            "transition_intentionality_score": 0.74,
            "chorus_emphasis_within_threshold": True,
            "slideshow_risk_within_threshold": True,
        },
    )

    assert report["publishability_summary"]["final_mv_publishability"]["rerender_bundle"] == {
        "action": "rerender_character_payoff_shots",
        "target_shots": ["S001", "S004", "S006"],
        "target_material_ids": ["MAT_001", "MAT_004", "MAT_006"],
        "target_section_ids": ["SEC_001", "SEC_004", "SEC_006"],
        "reason_codes": ["background_dominant_composition", "weak_character_payoff"],
    }



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


def test_review_models_build_review_stage_execution_payload_for_audio_sync_repairs():
    report = build_review_report(
        planned_shot_ids=["S001"],
        still_results=[{"shot_id": "S001", "image": "still-1.png"}],
        clip_results=[{"shot_id": "S001", "video": "clip-1.mp4"}],
        still_status={"S001": True},
        clip_status={"S001": True},
        final_video_exists=True,
        rerender_targets=["S001"],
        rerender_reasons={"S001": ["drift_too_high"]},
        audio_video_drift_sec=0.75,
        config={"review": {"max_audio_video_drift_sec": 0.5}},
        shot_plan=[{"shot_id": "S001", "render_mode": "ia2v"}],
        render_plan=[{"shot_id": "S001", "render_mode": "ia2v", "clip_prompt_seed": "clip-1"}],
        music_file="song.mp3",
        final_video_path="final.mp4",
    )

    assert report["rerender_execution_payloads"] == [
        {
            "shot_id": "S001",
            "recommended_action": "repair_audio_video_sync",
            "rerender_stage": "review",
            "workflow_focus": None,
            "prompt_contract_focus": [],
            "fix_strategy": "inspect_review_failures_manually",
            "stage_payloads": {
                "review": {
                    "final_video": "final.mp4",
                    "music_file": "song.mp3",
                    "recommended_action": "repair_audio_video_sync",
                    "target_shots": ["S001"],
                    "target_material_ids": [],
                    "target_section_ids": [],
                }
            },
        }
    ]


def test_classify_rerender_target_prioritizes_missing_assets_before_audio_sync_repair():
    classification = classify_rerender_target(["missing_still", "missing_clip", "drift_too_high"])

    assert classification["bucket"] == "technical_completion"
    assert classification["recommended_action"] == "rerender_missing_stills"



def test_classify_rerender_target_routes_assembly_failures_before_clip_rerender():
    classification = classify_rerender_target(["chorus_not_stronger_than_verse", "arbitrary_transitions"])

    assert classification["bucket"] == "final_mv_publishability"
    assert classification["recommended_action"] == "revise_assembly_weights_before_clip_rerender"
    assert classification["rerender_prescription"] == {
        "stage_focus": "review",
        "workflow_focus": None,
        "prompt_contract_focus": [],
        "fix_strategy": "revise_assembly_weights_before_clip_rerender",
    }



def test_review_models_route_assembly_only_failures_to_publishability_summary_before_clip_rerender():
    report = build_review_report(
        planned_shot_ids=["S001", "S002"],
        still_results=[{"shot_id": "S001"}, {"shot_id": "S002"}],
        clip_results=[{"shot_id": "S001"}, {"shot_id": "S002"}],
        still_status={"S001": True, "S002": True},
        clip_status={"S001": True, "S002": True},
        final_video_exists=True,
        rerender_targets=["S001"],
        rerender_reasons={"S001": ["chorus_not_stronger_than_verse", "arbitrary_transitions"]},
        audio_video_drift_sec=0.0,
        config={"review": {"max_audio_video_drift_sec": 0.5}},
        assembly_quality_summary={
            "chorus_emphasis_score": 0.5,
            "slideshow_risk_score": 0.41,
            "transition_intentionality_score": 0.3,
            "chorus_emphasis_within_threshold": False,
            "slideshow_risk_within_threshold": False,
        },
    )

    assert report["publishability_summary"]["final_mv_publishability"]["failed_checks"] == [
        "mood_consistency",
        "chorus_emphasis_within_threshold",
        "slideshow_risk_within_threshold",
    ]
    assert report["publishability_summary"]["final_mv_publishability"]["next_action"] == "revise_assembly_weights_before_clip_rerender"
    assert report["publishability_summary"]["final_mv_publishability"]["rerender_bundle"] == {
        "action": "revise_assembly_weights_before_clip_rerender",
        "target_shots": ["S001"],
        "target_material_ids": [],
        "target_section_ids": [],
        "reason_codes": ["arbitrary_transitions", "chorus_not_stronger_than_verse"],
    }



def test_review_models_do_not_enable_assembly_publishability_checks_from_partial_metadata_only():
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
        edit_intent_by_shot={"S001": {"section_emphasis": "chorus_push", "transition_in": "accent_in", "transition_out": "accent_out"}},
        render_count_by_shot={"S001": 1},
    )

    assert report["publishability_summary"]["final_mv_publishability"]["failed_checks"] == []
    assert report["publishability_summary"]["final_mv_publishability"]["next_action"] == "no_action"



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
        "target_material_ids": [],
        "target_section_ids": [],
        "reason_codes": [
            "unrelated_scene_intrusion",
            "weak_environment_match",
            "weak_subject_match",
        ],
    }
    assert report["publishability_summary"]["isolated_asset_quality"]["rerender_prescription"] == {
        "stage_focus": "stills",
        "workflow_focus": ["flux2_image"],
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
        "target_material_ids": [],
        "target_section_ids": [],
        "reason_codes": ["motion_fragile_frame"],
    }
    assert report["publishability_summary"]["final_mv_publishability"]["rerender_prescription"] == {
        "stage_focus": "stills_then_clips",
        "workflow_focus": ["flux2_image", "ia2v"],
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
        "target_material_ids": [],
        "target_section_ids": [],
        "reason_codes": [
            "collage_layout",
            "panel_layout",
            "split_screen",
        ],
    }
    assert report["publishability_summary"]["isolated_asset_quality"]["rerender_prescription"] == {
        "stage_focus": "stills",
        "workflow_focus": ["flux2_image"],
        "prompt_contract_focus": ["still_prompt_text"],
        "fix_strategy": "enforce_single_frame_keyframe_composition",
    }
