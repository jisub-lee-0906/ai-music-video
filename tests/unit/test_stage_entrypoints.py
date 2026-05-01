from pathlib import Path

from ai_mv.core.contracts.errors import StageFailure
from ai_mv.core.contracts.stage_io import StageInput, StageOutput
from ai_mv.core.orchestration.input_gate import validate_stage_input
from ai_mv.core.stages.assemble_mv import run_assemble_mv, _assembly_clip_segments
from ai_mv.core.stages.execute_rerender import run_execute_rerender
from ai_mv.core.stages.prepare_rerender import run_prepare_rerender
from ai_mv.core.stages.repair_audio_video_sync import run_repair_audio_video_sync
from ai_mv.core.stages.repair_rerender_prompts import run_repair_rerender_prompts
from ai_mv.core.stages.render_clips import _clip_prompt_text, run_render_clips
from ai_mv.core.stages.render_stills import _single_keyframe_prompt_text, _still_prompt_text, run_render_stills
from ai_mv.core.stages.rerender_escalation import run_rerender_escalation
from ai_mv.core.stages.rerender_loop import run_rerender_loop
from ai_mv.core.stages.rerender_review import run_rerender_review
from ai_mv.core.stages.review_outputs import run_review_outputs


def test_assemble_mv_propagates_edit_intent_into_review_inputs(monkeypatch, tmp_path):
    monkeypatch.setattr("ai_mv.core.stages.assemble_mv.resolve_generated_file", lambda _config, path, *_args: str(tmp_path / Path(path).name))
    monkeypatch.setattr("ai_mv.core.stages.assemble_mv.final_video_path", lambda _config, _run_id: tmp_path / "mv.mp4")
    monkeypatch.setattr("ai_mv.core.stages.assemble_mv.run_ffmpeg_mux", lambda *_args, **_kwargs: True)

    (tmp_path / "clip1.mp4").write_text("clip", encoding="utf-8")
    (tmp_path / "song.wav").write_text("audio", encoding="utf-8")

    stage_input = StageInput(
        run_id="run-assemble-edit-intent",
        config={},
        payload={
            "music_file": "song.wav",
            "clip_results": [{"shot_id": "S001", "video": "clip1.mp4", "material_id": "MAT_001", "section_id": "SEC_001"}],
            "render_plan": [
                {
                    "shot_id": "S001",
                    "section_id": "SEC_001",
                    "material_id": "MAT_001",
                    "edit_intent": {
                        "edit_priority": "high",
                        "section_emphasis": "chorus_push",
                        "target_clip_sec": 5.0,
                        "transition_in": "accent_in",
                        "transition_out": "accent_out",
                    },
                }
            ],
        },
    )

    out = run_assemble_mv(stage_input)

    assert out.payload["review_inputs"]["edit_intent_by_shot"] == {
        "S001": {
            "edit_priority": "high",
            "section_emphasis": "chorus_push",
            "target_clip_sec": 5.0,
            "transition_in": "accent_in",
            "transition_out": "accent_out",
        }
    }
    assert out.payload["assembly_plan"]["section_edits"][0]["section_id"] == "SEC_001"
    assert out.payload["assembly_plan"]["section_edits"][0]["selected_clip_ids"] == ["S001"]
    assert out.payload["assembly_plan"]["section_edits"][0]["selected_material_ids"] == ["MAT_001"]
    assert out.payload["assembly_plan"]["section_edits"][0]["transition_in"]
    assert out.payload["assembly_plan"]["section_edits"][0]["transition_out"]
    assert out.payload["assembly_plan"]["section_edit_map"]["SEC_001"]["selected_clip_ids"] == ["S001"]
    assert out.payload["assembly_plan"]["transition_map"]["SEC_001"]["transition_in"] == "accent_in"
    assert out.payload["assembly_plan"]["timing_map"]["SEC_001"]["selected_clip_ids"] == ["S001"]
    assert out.payload["assembly_plan"]["rejected_clip_map"] == {}



def test_assemble_mv_aggregates_multiple_shots_under_one_section_id(monkeypatch, tmp_path):
    monkeypatch.setattr("ai_mv.core.stages.assemble_mv.resolve_generated_file", lambda _config, path, *_args: str(tmp_path / Path(path).name))
    monkeypatch.setattr("ai_mv.core.stages.assemble_mv.final_video_path", lambda _config, _run_id: tmp_path / "mv-section-aggregate.mp4")
    monkeypatch.setattr("ai_mv.core.stages.assemble_mv.run_ffmpeg_mux", lambda *_args, **_kwargs: True)

    (tmp_path / "clip1.mp4").write_text("clip", encoding="utf-8")
    (tmp_path / "clip2.mp4").write_text("clip", encoding="utf-8")
    (tmp_path / "song.wav").write_text("audio", encoding="utf-8")

    stage_input = StageInput(
        run_id="run-assemble-section-aggregate",
        config={},
        payload={
            "music_file": "song.wav",
            "clip_results": [
                {"shot_id": "S001", "video": "clip1.mp4", "material_id": "MAT_001", "section_id": "SEC_001"},
                {"shot_id": "S002", "video": "clip2.mp4", "material_id": "MAT_002", "section_id": "SEC_001"},
            ],
            "render_plan": [
                {
                    "shot_id": "S001",
                    "section_id": "SEC_001",
                    "material_id": "MAT_001",
                    "edit_intent": {
                        "edit_priority": "high",
                        "target_clip_sec": 3.0,
                        "transition_in": "accent_in",
                        "transition_out": "cut_out",
                    },
                },
                {
                    "shot_id": "S002",
                    "section_id": "SEC_001",
                    "material_id": "MAT_002",
                    "edit_intent": {
                        "edit_priority": "medium",
                        "target_clip_sec": 2.0,
                        "transition_in": "cut_in",
                        "transition_out": "glide_out",
                    },
                },
            ],
        },
    )

    out = run_assemble_mv(stage_input)

    section_edit = out.payload["assembly_plan"]["section_edits"][0]
    assert section_edit["section_id"] == "SEC_001"
    assert section_edit["selected_clip_ids"] == ["S001", "S002"]
    assert section_edit["selected_material_ids"] == ["MAT_001", "MAT_002"]
    assert section_edit["coverage_sec"] == 5.0
    assert section_edit["trimmed_coverage_sec"] == 5.0
    assert section_edit["editorial_weight"] == "high"
    assert section_edit["transition_in"] == "accent_in"
    assert section_edit["transition_out"] == "glide_out"
    assert section_edit["trim_start_sec"] is None
    assert section_edit["trim_end_sec"] is None
    assert section_edit["snap_unit"] == "free"
    assert section_edit["cadence_profile"] == "support_hold"
    assert out.payload["assembly_plan"]["section_edit_map"]["SEC_001"]["selected_clip_ids"] == ["S001", "S002"]
    assert out.payload["assembly_plan"]["timing_map"]["SEC_001"]["selected_clip_ids"] == ["S001", "S002"]
    assert out.payload["assembly_plan"]["timing_map"]["SEC_001"]["trim_start_sec"] is None
    assert out.payload["assembly_plan"]["timing_map"]["SEC_001"]["trim_end_sec"] is None



def test_assemble_mv_propagates_render_planning_metadata_into_review_inputs(monkeypatch, tmp_path):
    monkeypatch.setattr("ai_mv.core.stages.assemble_mv.resolve_generated_file", lambda _config, path, *_args: str(tmp_path / Path(path).name))
    monkeypatch.setattr("ai_mv.core.stages.assemble_mv.final_video_path", lambda _config, _run_id: tmp_path / "mv-assembly-metadata.mp4")
    monkeypatch.setattr("ai_mv.core.stages.assemble_mv.run_ffmpeg_mux", lambda *_args, **_kwargs: True)

    (tmp_path / "clip1.mp4").write_text("clip", encoding="utf-8")
    (tmp_path / "song.wav").write_text("audio", encoding="utf-8")

    stage_input = StageInput(
        run_id="run-assemble-render-planning",
        config={},
        payload={
            "music_file": "song.wav",
            "clip_results": [{"shot_id": "S001", "video": "clip1.mp4"}],
            "render_plan": [
                {
                    "shot_id": "S001",
                    "render_count": 2,
                    "render_priority_score": 0.9,
                    "render_planning": {
                        "section_energy_score": 0.75,
                        "section_emphasis_score": 1.0,
                        "mode_importance_score": 1.0,
                        "lane_priority_score": 0.85,
                        "continuity_need_score": 1.0,
                        "render_priority_score": 0.9,
                    },
                }
            ],
        },
    )

    out = run_assemble_mv(stage_input)

    assert out.payload["review_inputs"]["render_count_by_shot"] == {"S001": 2}
    assert out.payload["review_inputs"]["render_priority_by_shot"] == {"S001": 0.9}
    assert out.payload["review_inputs"]["render_planning_by_shot"] == {
        "S001": {
            "section_energy_score": 0.75,
            "section_emphasis_score": 1.0,
            "mode_importance_score": 1.0,
            "lane_priority_score": 0.85,
            "continuity_need_score": 1.0,
            "render_priority_score": 0.9,
        }
    }



def test_assemble_mv_orders_clip_mux_and_timing_from_shot_plan(monkeypatch, tmp_path):
    mux_calls = {}

    monkeypatch.setattr("ai_mv.core.stages.assemble_mv.resolve_generated_file", lambda _config, path, *_args: str(tmp_path / Path(path).name))
    monkeypatch.setattr("ai_mv.core.stages.assemble_mv.final_video_path", lambda _config, _run_id: tmp_path / "mv-ordered.mp4")
    monkeypatch.setattr("ai_mv.core.stages.assemble_mv.ffprobe_duration", lambda _path: 0.0)

    def _fake_run_ffmpeg_mux(clips, *_args, **_kwargs):
        mux_calls["clip_names"] = [Path(item["path"]).name for item in clips]
        return True

    monkeypatch.setattr("ai_mv.core.stages.assemble_mv.run_ffmpeg_mux", _fake_run_ffmpeg_mux)

    for name in ("clip1.mp4", "clip2.mp4", "song.wav"):
        (tmp_path / name).write_text("x", encoding="utf-8")

    stage_input = StageInput(
        run_id="run-assemble-ordering",
        config={},
        payload={
            "music_file": "song.wav",
            "shot_plan": [
                {"shot_id": "S001", "section_id": "SEC_001"},
                {"shot_id": "S002", "section_id": "SEC_002"},
            ],
            "clip_results": [
                {"shot_id": "S002", "video": "clip2.mp4", "section_id": "SEC_002"},
                {"shot_id": "S001", "video": "clip1.mp4", "section_id": "SEC_001"},
            ],
            "render_plan": [
                {"shot_id": "S001", "section_id": "SEC_001", "edit_intent": {"target_clip_sec": 2.0}},
                {"shot_id": "S002", "section_id": "SEC_002", "edit_intent": {"target_clip_sec": 3.0}},
            ],
        },
    )

    out = run_assemble_mv(stage_input)

    assert mux_calls["clip_names"] == ["clip1.mp4", "clip2.mp4"]
    assert [section["section_id"] for section in out.payload["assembly_plan"]["section_edits"]] == ["SEC_001", "SEC_002"]
    assert out.payload["assembly_plan"]["timing_map"]["SEC_001"]["sequence_index"] == 0
    assert out.payload["assembly_plan"]["timing_map"]["SEC_002"]["sequence_index"] == 1


def test_assemble_mv_interleaves_candidate_roles_within_section_to_avoid_repetition(monkeypatch, tmp_path):
    mux_calls = {}

    monkeypatch.setattr("ai_mv.core.stages.assemble_mv.resolve_generated_file", lambda _config, path, *_args: str(tmp_path / Path(path).name))
    monkeypatch.setattr("ai_mv.core.stages.assemble_mv.final_video_path", lambda _config, _run_id: tmp_path / "mv-role-diverse.mp4")
    monkeypatch.setattr("ai_mv.core.stages.assemble_mv.ffprobe_duration", lambda _path: 4.0)

    def _fake_run_ffmpeg_mux(clips, *_args, **_kwargs):
        mux_calls["shot_ids"] = [item["shot_id"] for item in clips]
        return True

    monkeypatch.setattr("ai_mv.core.stages.assemble_mv.run_ffmpeg_mux", _fake_run_ffmpeg_mux)

    for name in ("hero1.mp4", "hero2.mp4", "world.mp4", "song.wav"):
        (tmp_path / name).write_text("x", encoding="utf-8")

    stage_input = StageInput(
        run_id="run-assemble-role-diverse",
        config={},
        payload={
            "music_file": "song.wav",
            "shot_plan": [
                {"shot_id": "S001", "section_id": "SEC_CHORUS"},
                {"shot_id": "S002", "section_id": "SEC_CHORUS"},
                {"shot_id": "S003", "section_id": "SEC_CHORUS"},
            ],
            "clip_results": [
                {"shot_id": "S001", "video": "hero1.mp4", "section_id": "SEC_CHORUS"},
                {"shot_id": "S002", "video": "hero2.mp4", "section_id": "SEC_CHORUS"},
                {"shot_id": "S003", "video": "world.mp4", "section_id": "SEC_CHORUS"},
            ],
            "render_plan": [
                {
                    "shot_id": "S001",
                    "section_id": "SEC_CHORUS",
                    "edit_intent": {"target_clip_sec": 1.0},
                    "production_policy": {
                        "candidate_role": "hero_face_performance",
                        "ia2v_risk_class": "green",
                        "anchor_reference_arm": "B_UPPER_ONLY",
                    },
                },
                {
                    "shot_id": "S002",
                    "section_id": "SEC_CHORUS",
                    "edit_intent": {"target_clip_sec": 1.0},
                    "production_policy": {
                        "candidate_role": "hero_face_performance",
                        "ia2v_risk_class": "green",
                        "anchor_reference_arm": "B_UPPER_ONLY",
                    },
                },
                {
                    "shot_id": "S003",
                    "section_id": "SEC_CHORUS",
                    "edit_intent": {"target_clip_sec": 1.0},
                    "production_policy": {
                        "candidate_role": "world_bridge",
                        "ia2v_risk_class": "green",
                        "anchor_reference_arm": "F_FULLBODY_UPPER_WORLD",
                    },
                },
            ],
        },
    )

    out = run_assemble_mv(stage_input)

    assert mux_calls["shot_ids"] == ["S001", "S003", "S002"]
    section = out.payload["assembly_plan"]["section_edits"][0]
    assert section["selected_clip_ids"] == ["S001", "S003", "S002"]
    assert section["candidate_roles"] == ["hero_face_performance", "world_bridge"]
    assert section["anchor_reference_arms"] == ["B_UPPER_ONLY", "F_FULLBODY_UPPER_WORLD"]



def test_assemble_mv_uses_edit_intent_to_build_trimmed_clip_segments(monkeypatch, tmp_path):
    clip1 = tmp_path / "clip1.mp4"
    clip2 = tmp_path / "clip2.mp4"
    monkeypatch.setattr("ai_mv.core.stages.assemble_mv.resolve_generated_file", lambda _config, path, *_args: str(path))
    segments = _assembly_clip_segments(
        {},
        {
            "shot_plan": [
                {"shot_id": "S001", "section_id": "SEC_001"},
                {"shot_id": "S002", "section_id": "SEC_002"},
            ],
            "clip_results": [
                {"shot_id": "S002", "video": str(clip2), "section_id": "SEC_002"},
                {"shot_id": "S001", "video": str(clip1), "section_id": "SEC_001"},
            ],
            "render_plan": [
                {
                    "shot_id": "S001",
                    "section_id": "SEC_001",
                    "edit_intent": {
                        "section_emphasis": "chorus_push",
                        "target_clip_sec": 2.0,
                        "transition_in": "accent_in",
                        "transition_out": "accent_out",
                    },
                },
                {
                    "shot_id": "S002",
                    "section_id": "SEC_002",
                    "edit_intent": {
                        "section_emphasis": "release_fade",
                        "target_clip_sec": 2.0,
                        "transition_in": "hold_in",
                        "transition_out": "fade_out",
                    },
                },
            ],
        },
        duration_by_shot={"S001": 5.0, "S002": 5.0},
    )

    assert [Path(segment["path"]).name for segment in segments] == ["clip1.mp4", "clip2.mp4"]
    assert segments[0]["trim_start_sec"] == 1.5
    assert segments[0]["trim_end_sec"] == 3.5
    assert segments[1]["trim_start_sec"] == 3.0
    assert segments[1]["trim_end_sec"] == 5.0



def test_assemble_mv_caps_high_risk_interaction_payoff_to_policy_duration(monkeypatch, tmp_path):
    clip1 = tmp_path / "clip1.mp4"
    monkeypatch.setattr("ai_mv.core.stages.assemble_mv.resolve_generated_file", lambda _config, path, *_args: str(path))

    segments = _assembly_clip_segments(
        {},
        {
            "clip_results": [{"shot_id": "S_PAYOFF", "video": str(clip1), "section_id": "SEC_FINAL"}],
            "render_plan": [
                {
                    "shot_id": "S_PAYOFF",
                    "section_id": "SEC_FINAL",
                    "edit_intent": {"section_emphasis": "chorus_push", "target_clip_sec": 4.0},
                    "production_policy": {
                        "candidate_role": "high_risk_interaction_payoff",
                        "ia2v_risk_class": "red",
                        "anchor_reference_arm": "D_FULLBODY_UPPER",
                        "recommended_duration_sec": {"min": 0.3, "max": 0.7},
                    },
                }
            ],
        },
        duration_by_shot={"S_PAYOFF": 4.0},
    )

    assert segments[0]["trim_start_sec"] == 1.65
    assert segments[0]["trim_end_sec"] == 2.35
    assert segments[0]["trimmed_coverage_sec"] == 0.7
    assert segments[0]["candidate_role"] == "high_risk_interaction_payoff"
    assert segments[0]["ia2v_risk_class"] == "red"
    assert segments[0]["anchor_reference_arm"] == "D_FULLBODY_UPPER"



def test_assemble_mv_surfaces_production_policy_in_review_inputs_and_assembly_plan(monkeypatch, tmp_path):
    monkeypatch.setattr("ai_mv.core.stages.assemble_mv.resolve_generated_file", lambda _config, path, *_args: str(tmp_path / Path(path).name))
    monkeypatch.setattr("ai_mv.core.stages.assemble_mv.final_video_path", lambda _config, _run_id: tmp_path / "mv-policy.mp4")
    monkeypatch.setattr("ai_mv.core.stages.assemble_mv.run_ffmpeg_mux", lambda *_args, **_kwargs: True)
    monkeypatch.setattr("ai_mv.core.stages.assemble_mv.ffprobe_duration", lambda _path: 4.0)

    (tmp_path / "clip1.mp4").write_text("clip", encoding="utf-8")
    (tmp_path / "song.wav").write_text("audio", encoding="utf-8")

    out = run_assemble_mv(
        StageInput(
            run_id="run-assemble-policy-context",
            config={},
            payload={
                "music_file": "song.wav",
                "clip_results": [{"shot_id": "S_PAYOFF", "video": "clip1.mp4", "section_id": "SEC_FINAL"}],
                "render_plan": [
                    {
                        "shot_id": "S_PAYOFF",
                        "section_id": "SEC_FINAL",
                        "edit_intent": {"section_emphasis": "chorus_push", "target_clip_sec": 4.0},
                        "production_policy": {
                            "candidate_role": "high_risk_interaction_payoff",
                            "ia2v_risk_class": "red",
                            "anchor_reference_arm": "D_FULLBODY_UPPER",
                            "recommended_duration_sec": {"min": 0.3, "max": 0.7},
                        },
                    }
                ],
            },
        )
    )

    assert out.payload["review_inputs"]["production_policy_by_shot"]["S_PAYOFF"]["ia2v_risk_class"] == "red"
    section = out.payload["assembly_plan"]["section_edit_map"]["SEC_FINAL"]
    timing = out.payload["assembly_plan"]["timing_map"]["SEC_FINAL"]
    assert section["ia2v_risk_class"] == "red"
    assert section["candidate_roles"] == ["high_risk_interaction_payoff"]
    assert timing["ia2v_risk_class"] == "red"
    assert timing["candidate_roles"] == ["high_risk_interaction_payoff"]



def test_assemble_mv_uses_pattern_family_to_split_chorus_trim_behavior(monkeypatch, tmp_path):
    clip1 = tmp_path / "clip1.mp4"
    clip2 = tmp_path / "clip2.mp4"
    monkeypatch.setattr("ai_mv.core.stages.assemble_mv.resolve_generated_file", lambda _config, path, *_args: str(path))

    segments = _assembly_clip_segments(
        {},
        {
            "shot_plan": [
                {"shot_id": "S001", "section_id": "SEC_001"},
                {"shot_id": "S002", "section_id": "SEC_002"},
            ],
            "clip_results": [
                {"shot_id": "S001", "video": str(clip1), "section_id": "SEC_001"},
                {"shot_id": "S002", "video": str(clip2), "section_id": "SEC_002"},
            ],
            "render_plan": [
                {
                    "shot_id": "S001",
                    "section_id": "SEC_001",
                    "edit_intent": {
                        "section_emphasis": "chorus_push",
                        "pattern_family": "hook_punch_in",
                        "target_clip_sec": 2.4,
                        "transition_in": "accent_in",
                        "transition_out": "accent_out",
                    },
                },
                {
                    "shot_id": "S002",
                    "section_id": "SEC_002",
                    "edit_intent": {
                        "section_emphasis": "chorus_push",
                        "pattern_family": "hook_sustain",
                        "target_clip_sec": 2.4,
                        "transition_in": "glide_in",
                        "transition_out": "accent_out",
                    },
                },
            ],
        },
        duration_by_shot={"S001": 6.0, "S002": 6.0},
    )

    assert segments[0]["trim_start_sec"] == 1.8
    assert segments[0]["trim_end_sec"] == 4.2
    assert segments[1]["trim_start_sec"] == 0.9
    assert segments[1]["trim_end_sec"] == 3.3
    assert segments[0]["cadence_profile"] == "hook_dense"
    assert segments[1]["cadence_profile"] == "hook_dense"



def test_assemble_mv_uses_pattern_family_to_split_support_trim_behavior(monkeypatch, tmp_path):
    clip1 = tmp_path / "clip1.mp4"
    clip2 = tmp_path / "clip2.mp4"
    monkeypatch.setattr("ai_mv.core.stages.assemble_mv.resolve_generated_file", lambda _config, path, *_args: str(path))

    segments = _assembly_clip_segments(
        {},
        {
            "shot_plan": [
                {"shot_id": "S001", "section_id": "SEC_001"},
                {"shot_id": "S002", "section_id": "SEC_002"},
            ],
            "clip_results": [
                {"shot_id": "S001", "video": str(clip1), "section_id": "SEC_001"},
                {"shot_id": "S002", "video": str(clip2), "section_id": "SEC_002"},
            ],
            "render_plan": [
                {
                    "shot_id": "S001",
                    "section_id": "SEC_001",
                    "edit_intent": {
                        "section_emphasis": "sequence_support",
                        "pattern_family": "support_drive",
                        "target_clip_sec": 2.7,
                        "transition_in": "cut_in",
                        "transition_out": "cut_out",
                    },
                },
                {
                    "shot_id": "S002",
                    "section_id": "SEC_002",
                    "edit_intent": {
                        "section_emphasis": "sequence_support",
                        "pattern_family": "support_hold",
                        "target_clip_sec": 4.2,
                        "transition_in": "hold_in",
                        "transition_out": "cut_out",
                    },
                },
            ],
        },
        duration_by_shot={"S001": 6.0, "S002": 6.0},
    )

    assert segments[0]["trim_start_sec"] == 0.495
    assert segments[0]["trim_end_sec"] == 3.195
    assert segments[1]["trim_start_sec"] == 0.0
    assert segments[1]["trim_end_sec"] == 4.2
    assert segments[0]["cadence_profile"] == "support_release"
    assert segments[1]["cadence_profile"] == "support_hold"



def test_assemble_mv_exposes_cadence_profile_and_snap_summary_in_assembly_plan(monkeypatch, tmp_path):
    monkeypatch.setattr("ai_mv.core.stages.assemble_mv.resolve_generated_file", lambda _config, path, *_args: str(tmp_path / Path(path).name))
    monkeypatch.setattr("ai_mv.core.stages.assemble_mv.final_video_path", lambda _config, _run_id: tmp_path / "mv-cadence.mp4")
    monkeypatch.setattr("ai_mv.core.stages.assemble_mv.run_ffmpeg_mux", lambda *_args, **_kwargs: True)
    monkeypatch.setattr("ai_mv.core.stages.assemble_mv.ffprobe_duration", lambda _path: 5.0)

    (tmp_path / "clip1.mp4").write_text("clip", encoding="utf-8")
    (tmp_path / "clip2.mp4").write_text("clip", encoding="utf-8")
    (tmp_path / "song.wav").write_text("audio", encoding="utf-8")

    out = run_assemble_mv(
        StageInput(
            run_id="run-assemble-cadence-summary",
            config={},
            payload={
                "music_file": "song.wav",
                "audio_map": {
                    "timing": {
                        "bar_times_sec": [0.0, 2.0, 4.0, 6.0, 8.0],
                        "grid_beat_times_sec": [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0],
                    }
                },
                "shot_plan": [
                    {"shot_id": "S001", "section_id": "SEC_001", "start_sec": 0.0, "duration_sec": 5.0},
                    {"shot_id": "S002", "section_id": "SEC_002", "start_sec": 5.0, "duration_sec": 5.0},
                ],
                "clip_results": [
                    {"shot_id": "S001", "video": "clip1.mp4", "section_id": "SEC_001", "material_id": "MAT_001"},
                    {"shot_id": "S002", "video": "clip2.mp4", "section_id": "SEC_002", "material_id": "MAT_002"},
                ],
                "render_plan": [
                    {
                        "shot_id": "S001",
                        "section_id": "SEC_001",
                        "material_id": "MAT_001",
                        "edit_intent": {
                            "edit_priority": "high",
                            "section_emphasis": "chorus_push",
                            "target_clip_sec": 2.1,
                            "transition_in": "accent_in",
                            "transition_out": "accent_out",
                        },
                    },
                    {
                        "shot_id": "S002",
                        "section_id": "SEC_002",
                        "material_id": "MAT_002",
                        "edit_intent": {
                            "edit_priority": "medium",
                            "section_emphasis": "sequence_support",
                            "target_clip_sec": 2.1,
                            "transition_in": "cut_in",
                            "transition_out": "cut_out",
                        },
                    },
                ],
            },
        )
    )

    sec1 = out.payload["assembly_plan"]["section_edit_map"]["SEC_001"]
    sec2 = out.payload["assembly_plan"]["section_edit_map"]["SEC_002"]
    time1 = out.payload["assembly_plan"]["timing_map"]["SEC_001"]
    time2 = out.payload["assembly_plan"]["timing_map"]["SEC_002"]

    assert sec1["cadence_profile"] == "hook_dense"
    assert sec1["snap_unit"] == "bar"
    assert sec1["trim_start_sec"] == 2.0
    assert sec1["trim_end_sec"] == 4.0
    assert time1["snap_unit"] == "bar"
    assert time1["cadence_profile"] == "hook_dense"
    assert time1["trimmed_coverage_sec"] == 2.0

    assert sec2["cadence_profile"] == "support_hold"
    assert sec2["snap_unit"] == "beat"
    assert sec2["trim_start_sec"] == 0.0
    assert sec2["trim_end_sec"] == 1.0
    assert time2["snap_unit"] == "beat"
    assert time2["cadence_profile"] == "support_hold"
    assert time2["trimmed_coverage_sec"] == 1.0



def test_assemble_mv_marks_free_snap_when_audio_timing_is_missing(monkeypatch, tmp_path):
    monkeypatch.setattr("ai_mv.core.stages.assemble_mv.resolve_generated_file", lambda _config, path, *_args: str(tmp_path / Path(path).name))
    monkeypatch.setattr("ai_mv.core.stages.assemble_mv.final_video_path", lambda _config, _run_id: tmp_path / "mv-free-snap.mp4")
    monkeypatch.setattr("ai_mv.core.stages.assemble_mv.run_ffmpeg_mux", lambda *_args, **_kwargs: True)
    monkeypatch.setattr("ai_mv.core.stages.assemble_mv.ffprobe_duration", lambda _path: 5.0)

    (tmp_path / "clip1.mp4").write_text("clip", encoding="utf-8")
    (tmp_path / "song.wav").write_text("audio", encoding="utf-8")

    out = run_assemble_mv(
        StageInput(
            run_id="run-assemble-free-snap",
            config={},
            payload={
                "music_file": "song.wav",
                "shot_plan": [{"shot_id": "S001", "section_id": "SEC_001", "start_sec": 0.0, "duration_sec": 5.0}],
                "clip_results": [{"shot_id": "S001", "video": "clip1.mp4", "section_id": "SEC_001"}],
                "render_plan": [
                    {
                        "shot_id": "S001",
                        "section_id": "SEC_001",
                        "edit_intent": {
                            "edit_priority": "medium",
                            "section_emphasis": "bridge_contrast",
                            "target_clip_sec": 2.0,
                            "transition_in": "glide_in",
                            "transition_out": "handoff_out",
                        },
                    }
                ],
            },
        )
    )

    sec1 = out.payload["assembly_plan"]["section_edit_map"]["SEC_001"]
    time1 = out.payload["assembly_plan"]["timing_map"]["SEC_001"]

    assert sec1["cadence_profile"] == "bridge_pivot"
    assert sec1["snap_unit"] == "free"
    assert sec1["trim_start_sec"] == 3.0
    assert sec1["trim_end_sec"] == 5.0
    assert time1["snap_unit"] == "free"
    assert time1["trimmed_coverage_sec"] == 2.0



def test_assembly_clip_segments_use_actual_clip_duration_when_target_exceeds_clip(monkeypatch, tmp_path):
    clip1 = tmp_path / "clip1.mp4"
    monkeypatch.setattr("ai_mv.core.stages.assemble_mv.resolve_generated_file", lambda _config, path, *_args: str(path))

    segments = _assembly_clip_segments(
        {},
        {
            "shot_plan": [{"shot_id": "S001", "section_id": "SEC_001", "start_sec": 0.0, "duration_sec": 2.0}],
            "clip_results": [{"shot_id": "S001", "video": str(clip1), "section_id": "SEC_001"}],
            "render_plan": [
                {
                    "shot_id": "S001",
                    "section_id": "SEC_001",
                    "edit_intent": {
                        "section_emphasis": "sequence_support",
                        "target_clip_sec": 3.0,
                        "transition_in": "cut_in",
                        "transition_out": "cut_out",
                    },
                }
            ],
        },
        duration_by_shot={"S001": 2.0},
    )

    assert segments[0]["trim_start_sec"] is None
    assert segments[0]["trim_end_sec"] is None
    assert segments[0]["trimmed_coverage_sec"] == 2.0



def test_assemble_mv_snaps_chorus_trim_to_bar_grid_when_audio_timing_exists(monkeypatch, tmp_path):
    clip1 = tmp_path / "clip1.mp4"
    monkeypatch.setattr("ai_mv.core.stages.assemble_mv.resolve_generated_file", lambda _config, path, *_args: str(path))

    segments = _assembly_clip_segments(
        {},
        {
            "audio_map": {
                "timing": {
                    "bar_times_sec": [0.0, 2.0, 4.0, 6.0, 8.0],
                    "grid_beat_times_sec": [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0],
                }
            },
            "shot_plan": [
                {"shot_id": "S001", "section_id": "SEC_001", "start_sec": 0.0, "duration_sec": 5.0},
            ],
            "clip_results": [
                {"shot_id": "S001", "video": str(clip1), "section_id": "SEC_001"},
            ],
            "render_plan": [
                {
                    "shot_id": "S001",
                    "section_id": "SEC_001",
                    "edit_intent": {
                        "section_emphasis": "chorus_push",
                        "target_clip_sec": 2.1,
                        "transition_in": "accent_in",
                        "transition_out": "accent_out",
                    },
                },
            ],
        },
        duration_by_shot={"S001": 5.0},
    )

    assert segments[0]["trim_start_sec"] == 2.0
    assert segments[0]["trim_end_sec"] == 4.0



def test_assemble_mv_snaps_support_trim_to_beat_grid_when_audio_timing_exists(monkeypatch, tmp_path):
    clip1 = tmp_path / "clip1.mp4"
    monkeypatch.setattr("ai_mv.core.stages.assemble_mv.resolve_generated_file", lambda _config, path, *_args: str(path))

    segments = _assembly_clip_segments(
        {},
        {
            "audio_map": {
                "timing": {
                    "bar_times_sec": [0.0, 2.0, 4.0, 6.0, 8.0],
                    "grid_beat_times_sec": [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0],
                }
            },
            "shot_plan": [
                {"shot_id": "S001", "section_id": "SEC_001", "start_sec": 0.0, "duration_sec": 5.0},
            ],
            "clip_results": [
                {"shot_id": "S001", "video": str(clip1), "section_id": "SEC_001"},
            ],
            "render_plan": [
                {
                    "shot_id": "S001",
                    "section_id": "SEC_001",
                    "edit_intent": {
                        "section_emphasis": "sequence_support",
                        "target_clip_sec": 2.1,
                        "transition_in": "cut_in",
                        "transition_out": "cut_out",
                    },
                },
            ],
        },
        duration_by_shot={"S001": 5.0},
    )

    assert segments[0]["trim_start_sec"] == 0.0
    assert segments[0]["trim_end_sec"] == 2.0



def test_assemble_mv_leaves_trim_unchanged_when_no_timing_markers_fall_inside_shot(monkeypatch, tmp_path):
    clip1 = tmp_path / "clip1.mp4"
    monkeypatch.setattr("ai_mv.core.stages.assemble_mv.resolve_generated_file", lambda _config, path, *_args: str(path))

    segments = _assembly_clip_segments(
        {},
        {
            "audio_map": {
                "timing": {
                    "bar_times_sec": [0.0, 2.0, 4.0, 6.0, 8.0],
                    "grid_beat_times_sec": [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0],
                }
            },
            "shot_plan": [
                {"shot_id": "S001", "section_id": "SEC_001", "start_sec": 10.0, "duration_sec": 5.0},
            ],
            "clip_results": [
                {"shot_id": "S001", "video": str(clip1), "section_id": "SEC_001"},
            ],
            "render_plan": [
                {
                    "shot_id": "S001",
                    "section_id": "SEC_001",
                    "edit_intent": {
                        "section_emphasis": "chorus_push",
                        "target_clip_sec": 2.1,
                        "transition_in": "accent_in",
                        "transition_out": "accent_out",
                    },
                },
            ],
        },
        duration_by_shot={"S001": 5.0},
    )

    assert segments[0]["trim_start_sec"] == 1.45
    assert segments[0]["trim_end_sec"] == 3.55



def test_assemble_mv_leaves_trim_unchanged_when_shot_plan_row_is_missing(monkeypatch, tmp_path):
    clip1 = tmp_path / "clip1.mp4"
    monkeypatch.setattr("ai_mv.core.stages.assemble_mv.resolve_generated_file", lambda _config, path, *_args: str(path))

    segments = _assembly_clip_segments(
        {},
        {
            "audio_map": {
                "timing": {
                    "bar_times_sec": [0.0, 2.0, 4.0, 6.0, 8.0],
                    "grid_beat_times_sec": [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0],
                }
            },
            "shot_plan": [],
            "clip_results": [
                {"shot_id": "S001", "video": str(clip1), "section_id": "SEC_001"},
            ],
            "render_plan": [
                {
                    "shot_id": "S001",
                    "section_id": "SEC_001",
                    "edit_intent": {
                        "section_emphasis": "chorus_push",
                        "target_clip_sec": 2.1,
                        "transition_in": "accent_in",
                        "transition_out": "accent_out",
                    },
                },
            ],
        },
        duration_by_shot={"S001": 5.0},
    )

    assert segments[0]["trim_start_sec"] == 1.45
    assert segments[0]["trim_end_sec"] == 3.55



def test_assemble_mv_caps_snapped_trim_to_actual_clip_duration(monkeypatch, tmp_path):
    clip1 = tmp_path / "clip1.mp4"
    monkeypatch.setattr("ai_mv.core.stages.assemble_mv.resolve_generated_file", lambda _config, path, *_args: str(path))

    segments = _assembly_clip_segments(
        {},
        {
            "audio_map": {
                "timing": {
                    "bar_times_sec": [0.0, 2.0, 4.0, 6.0, 8.0],
                    "grid_beat_times_sec": [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0],
                }
            },
            "shot_plan": [
                {"shot_id": "S001", "section_id": "SEC_001", "start_sec": 0.0, "duration_sec": 8.0},
            ],
            "clip_results": [
                {"shot_id": "S001", "video": str(clip1), "section_id": "SEC_001"},
            ],
            "render_plan": [
                {
                    "shot_id": "S001",
                    "section_id": "SEC_001",
                    "edit_intent": {
                        "section_emphasis": "release_fade",
                        "target_clip_sec": 2.1,
                        "transition_in": "hold_in",
                        "transition_out": "fade_out",
                    },
                },
            ],
        },
        duration_by_shot={"S001": 5.0},
    )

    assert segments[0]["trim_end_sec"] <= 5.0



def test_assemble_mv_falls_back_to_beat_grid_when_bar_grid_has_too_few_markers(monkeypatch, tmp_path):
    clip1 = tmp_path / "clip1.mp4"
    monkeypatch.setattr("ai_mv.core.stages.assemble_mv.resolve_generated_file", lambda _config, path, *_args: str(path))

    segments = _assembly_clip_segments(
        {},
        {
            "audio_map": {
                "timing": {
                    "bar_times_sec": [2.0],
                    "grid_beat_times_sec": [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0],
                }
            },
            "shot_plan": [
                {"shot_id": "S001", "section_id": "SEC_001", "start_sec": 0.0, "duration_sec": 3.3},
            ],
            "clip_results": [
                {"shot_id": "S001", "video": str(clip1), "section_id": "SEC_001"},
            ],
            "render_plan": [
                {
                    "shot_id": "S001",
                    "section_id": "SEC_001",
                    "edit_intent": {
                        "section_emphasis": "chorus_push",
                        "target_clip_sec": 1.1,
                        "transition_in": "accent_in",
                        "transition_out": "accent_out",
                    },
                },
            ],
        },
        duration_by_shot={"S001": 3.3},
    )

    assert segments[0]["trim_start_sec"] == 1.0
    assert segments[0]["trim_end_sec"] == 2.0


def test_render_stills_uses_generic_fallback_prompt_text_when_empty():
    prompt = _still_prompt_text({})

    assert prompt
    assert "city pop" not in prompt.lower()


def test_render_clips_uses_generic_fallback_prompt_text_when_empty():
    prompt = _clip_prompt_text({})

    assert prompt
    assert "city pop" not in prompt.lower()


def test_render_stills_prefers_workflow_specific_still_prompt_text():
    prompt = _still_prompt_text({"still_prompt_text": "single-subject keyframe, motion-safe keyframe"})

    assert prompt == "single-subject keyframe, motion-safe keyframe"


def test_render_clips_prefers_workflow_specific_clip_prompt_seed():
    prompt = _clip_prompt_text({"clip_prompt_seed": "camera drift forward, stable motion"})

    assert prompt == "camera drift forward, stable motion"


def test_render_clips_does_not_fall_back_to_still_facing_prompt_polish_for_seed_text():
    prompt = _clip_prompt_text(
        {
            "prompt_seed": "night drive style seed",
            "prompt_polish": "single cinematic keyframe, one uninterrupted composition, no collage",
            "prompt_draft": "still-only dramatic tableau",
        }
    )

    assert prompt == "night drive style seed"
    assert "single cinematic keyframe" not in prompt


def test_render_clips_uses_compact_positive_fallback_instead_of_prompt_polish(monkeypatch):
    calls = []

    def _fake_run_ltx_ia2v(_config, item):
        calls.append(dict(item))
        return f"D:/renders/{item['shot_id']}_ia2v.mp4"

    monkeypatch.setattr("ai_mv.core.stages.render_clips.run_ltx_ia2v", _fake_run_ltx_ia2v)
    stage_input = StageInput(
        run_id="run-clip-fallback-compact",
        config={"render": {"ltx_negative": "bad", "ltx_fps": 24, "ltx_default_shot_sec": 4.0}},
        payload={
            "music_file": "music/song.mp3",
            "shot_plan": [{"shot_id": "S002", "duration_sec": 5.0, "render_mode": "ia2v", "start_sec": 0.0}],
            "render_plan": [
                {
                    "shot_id": "S002",
                    "render_mode": "ia2v",
                    "prompt_seed": "night drive style seed",
                    "prompt_polish": "single cinematic keyframe, one uninterrupted composition, no collage",
                    "prompt_draft": "still-only dramatic tableau",
                }
            ],
            "still_results": [{"shot_id": "S002", "image": "D:/renders/S002.png"}],
        },
    )

    run_render_clips(stage_input)

    assert calls[0]["prompt_seed"] == "night drive style seed"
    assert calls[0]["positive_prompt"] == "night drive style seed"
    assert "single cinematic keyframe" not in calls[0]["positive_prompt"]


def test_render_stills_calls_flux2_runner(monkeypatch):
    calls = []

    def _fake_run_flux2_still(_config, item):
        calls.append(item)
        return f"D:/renders/{item['shot_id']}.png"

    monkeypatch.setattr("ai_mv.core.stages.render_stills.run_flux2_still", _fake_run_flux2_still)
    stage_input = StageInput(
        run_id="run-1",
        config={"render": {"flux2_size": "1024x1024"}},
        payload={
            "shot_plan": [{"shot_id": "S001", "material_id": "MAT_001"}],
            "material_plan": [{"material_id": "MAT_001", "section_id": "SEC_001"}],
            "render_plan": [{"shot_id": "S001", "material_id": "MAT_001", "prompt_seed": "city pop girl by the sea"}],
        },
    )

    out = run_render_stills(stage_input)

    assert out.payload["still_results"][0]["image"] == "D:/renders/S001.png"
    assert out.payload["still_results"][0]["material_id"] == "MAT_001"
    assert calls[0]["filename_prefix"] == "ai_mv/runs/run-1/stills/shot-S001"
    assert "city pop girl by the sea" in calls[0]["positive_prompt"]
    assert "single cinematic keyframe" in calls[0]["positive_prompt"]
    assert "one uninterrupted composition" in calls[0]["positive_prompt"]
    assert "negative_prompt" not in calls[0]
    assert "seed" not in calls[0]


def test_render_stills_does_not_reuse_prior_still_as_reference_by_default(monkeypatch):
    calls = []

    def _fake_run_flux2_still(_config, item):
        calls.append(item)
        return f"D:/renders/{item['shot_id']}.png"

    monkeypatch.setattr("ai_mv.core.stages.render_stills.run_flux2_still", _fake_run_flux2_still)
    stage_input = StageInput(
        run_id="run-no-reference-default",
        config={"render": {"flux2_size": "1280x720"}},
        payload={
            "shot_plan": [{"shot_id": "S001", "material_id": "MAT_001"}],
            "material_plan": [{"material_id": "MAT_001", "section_id": "SEC_001"}],
            "render_plan": [{"shot_id": "S001", "material_id": "MAT_001", "prompt_seed": "city pop girl by the sea"}],
            "still_results": [{"shot_id": "S001", "image": "D:/renders/older-S001.png"}],
        },
    )

    run_render_stills(stage_input)

    assert "reference_image" not in calls[0]


def test_render_stills_uses_render_count_for_candidate_exploration(monkeypatch):
    calls = []

    def _fake_run_flux2_still(_config, item):
        calls.append(dict(item))
        retry = int(item.get("retry", 0) or 0)
        return f"D:/renders/{item['shot_id']}_candidate_{retry}.png"

    monkeypatch.setattr("ai_mv.core.stages.render_stills.run_flux2_still", _fake_run_flux2_still)
    stage_input = StageInput(
        run_id="run-render-count-candidates",
        config={"render": {"flux2_size": "1280x720"}},
        payload={
            "shot_plan": [{"shot_id": "S010", "material_id": "MAT_010"}],
            "material_plan": [{"material_id": "MAT_010", "section_id": "SEC_010"}],
            "render_plan": [{"shot_id": "S010", "material_id": "MAT_010", "prompt_seed": "city pop boulevard", "render_count": 3, "seed": 100}],
        },
    )

    out = run_render_stills(stage_input)

    assert len(calls) == 3
    assert [call.get("retry") for call in calls] == [0, 1, 2]
    assert [call.get("seed") for call in calls] == [100, 101, 102]
    assert out.payload["still_results"][0]["image"] == "D:/renders/S010_candidate_0.png"
    assert out.payload["still_results"][0]["material_id"] == "MAT_010"
    assert out.payload["still_results"][0]["candidate_images"] == [
        "D:/renders/S010_candidate_0.png",
        "D:/renders/S010_candidate_1.png",
        "D:/renders/S010_candidate_2.png",
    ]
    assert out.payload["still_results"][0]["candidate_count"] == 3
    assert out.payload["still_results"][0]["selected_candidate_index"] == 0
    assert out.payload["still_results"][0]["selection_policy"] == "first_candidate"
    assert out.payload["still_results"][0]["selected_candidate"]["image"] == "D:/renders/S010_candidate_0.png"



def test_render_stills_can_select_non_default_candidate_by_explicit_index(monkeypatch):
    calls = []

    def _fake_run_flux2_still(_config, item):
        calls.append(dict(item))
        retry = int(item.get("retry", 0) or 0)
        return f"D:/renders/{item['shot_id']}_candidate_{retry}.png"

    monkeypatch.setattr("ai_mv.core.stages.render_stills.run_flux2_still", _fake_run_flux2_still)
    stage_input = StageInput(
        run_id="run-render-count-selection",
        config={"render": {"flux2_size": "1280x720"}},
        payload={
            "shot_plan": [{"shot_id": "S011", "material_id": "MAT_011"}],
            "material_plan": [{"material_id": "MAT_011", "section_id": "SEC_011"}],
            "render_plan": [
                {
                    "shot_id": "S011",
                    "material_id": "MAT_011",
                    "prompt_seed": "city pop boulevard",
                    "render_count": 3,
                    "seed": 100,
                    "still_selection_index": 2,
                }
            ],
        },
    )

    out = run_render_stills(stage_input)

    assert len(calls) == 3
    assert out.payload["still_results"][0]["image"] == "D:/renders/S011_candidate_2.png"
    assert out.payload["still_results"][0]["selected_candidate_index"] == 2
    assert out.payload["still_results"][0]["selection_policy"] == "explicit_index"
    assert out.payload["still_results"][0]["selected_candidate"]["retry"] == 2
    assert out.payload["still_results"][0]["selected_candidate"]["seed"] == 102



def test_render_stills_prefers_highest_continuity_candidate_when_scores_present(monkeypatch):
    def _fake_run_flux2_still(_config, item):
        retry = int(item.get("retry", 0) or 0)
        return f"D:/renders/{item['shot_id']}_candidate_{retry}.png"

    monkeypatch.setattr("ai_mv.core.stages.render_stills.run_flux2_still", _fake_run_flux2_still)
    stage_input = StageInput(
        run_id="run-render-continuity-selection",
        config={"render": {"flux2_size": "1280x720"}},
        payload={
            "shot_plan": [
                {
                    "shot_id": "S012",
                    "material_id": "MAT_012",
                    "protagonist_anchor": "same lone protagonist",
                    "world_anchor": "same rain-slick neon boulevard world",
                }
            ],
            "material_plan": [{"material_id": "MAT_012", "section_id": "SEC_012"}],
            "render_plan": [
                {
                    "shot_id": "S012",
                    "material_id": "MAT_012",
                    "prompt_seed": "city pop boulevard",
                    "render_count": 3,
                    "seed": 200,
                    "continuity_contract": {
                        "protagonist_anchor": "same lone protagonist",
                        "world_anchor": "same rain-slick neon boulevard world",
                    },
                    "still_candidate_scores": [
                        {"continuity_score": 0.41, "identity_score": 0.50, "world_score": 0.50},
                        {"continuity_score": 0.93, "identity_score": 0.91, "world_score": 0.90},
                        {"continuity_score": 0.72, "identity_score": 0.70, "world_score": 0.74},
                    ],
                }
            ],
        },
    )

    out = run_render_stills(stage_input)

    assert out.payload["still_results"][0]["image"] == "D:/renders/S012_candidate_1.png"
    assert out.payload["still_results"][0]["selected_candidate_index"] == 1
    assert out.payload["still_results"][0]["selection_policy"] == "continuity_score"
    assert out.payload["still_results"][0]["selected_candidate"]["continuity_score"] == 0.93
    assert out.payload["still_results"][0]["selected_candidate"]["identity_score"] == 0.91
    assert out.payload["still_results"][0]["selected_candidate"]["world_score"] == 0.9



def test_render_stills_keeps_first_candidate_when_continuity_scores_are_partial(monkeypatch):
    def _fake_run_flux2_still(_config, item):
        retry = int(item.get("retry", 0) or 0)
        return f"D:/renders/{item['shot_id']}_candidate_{retry}.png"

    monkeypatch.setattr("ai_mv.core.stages.render_stills.run_flux2_still", _fake_run_flux2_still)
    stage_input = StageInput(
        run_id="run-render-partial-continuity-selection",
        config={"render": {"flux2_size": "1280x720"}},
        payload={
            "shot_plan": [{"shot_id": "S013", "material_id": "MAT_013"}],
            "material_plan": [{"material_id": "MAT_013", "section_id": "SEC_013"}],
            "render_plan": [
                {
                    "shot_id": "S013",
                    "material_id": "MAT_013",
                    "prompt_seed": "city pop boulevard",
                    "render_count": 2,
                    "seed": 300,
                    "continuity_contract": {
                        "protagonist_anchor": "same lone protagonist",
                        "world_anchor": "same rain-slick neon boulevard world",
                    },
                    "still_candidate_scores": [
                        {},
                        {"identity_score": 0.95, "world_score": 0.94},
                    ],
                }
            ],
        },
    )

    out = run_render_stills(stage_input)

    assert out.payload["still_results"][0]["image"] == "D:/renders/S013_candidate_0.png"
    assert out.payload["still_results"][0]["selected_candidate_index"] == 0
    assert out.payload["still_results"][0]["selection_policy"] == "first_candidate"



def test_gate_requires_material_plan_for_stills_contract():
    import pytest

    with pytest.raises(StageFailure):
        validate_stage_input(
            "stills",
            {
                "shot_plan": [{"shot_id": "S001", "material_id": "MAT_001"}],
                "render_plan": [{"shot_id": "S001", "material_id": "MAT_001", "render_mode": "ia2v"}],
                "style_bible": {"style": "synthwave"},
            },
        )


def test_render_stills_can_explicitly_reuse_prior_still_as_reference(monkeypatch):
    calls = []

    def _fake_run_flux2_still(_config, item):
        calls.append(item)
        return f"D:/renders/{item['shot_id']}.png"

    monkeypatch.setattr("ai_mv.core.stages.render_stills.run_flux2_still", _fake_run_flux2_still)
    stage_input = StageInput(
        run_id="run-reference-explicit",
        config={"render": {"flux2_size": "1280x720"}},
        payload={
            "shot_plan": [{"shot_id": "S001"}],
            "render_plan": [{"shot_id": "S001", "prompt_seed": "city pop girl by the sea", "reference_mode": "reuse_prior_still"}],
            "still_results": [{"shot_id": "S001", "image": "D:/renders/older-S001.png"}],
        },
    )

    run_render_stills(stage_input)

    assert calls[0]["reference_image"] == "D:/renders/older-S001.png"



def test_render_stills_reuse_prior_still_does_not_fallback_to_other_anchor_when_same_shot_prior_is_missing(monkeypatch):
    calls = []

    def _fake_run_flux2_still(_config, item):
        calls.append(dict(item))
        return f"D:/renders/{item['shot_id']}.png"

    monkeypatch.setattr("ai_mv.core.stages.render_stills.run_flux2_still", _fake_run_flux2_still)
    stage_input = StageInput(
        run_id="run-reference-explicit-missing",
        config={"render": {"flux2_size": "1280x720"}},
        payload={
            "shot_plan": [{"shot_id": "S001"}],
            "render_plan": [{"shot_id": "S001", "prompt_seed": "city pop girl by the sea", "reference_mode": "reuse_prior_still"}],
            "still_results": [{"shot_id": "S999", "image": "D:/renders/other-anchor.png", "reference_mode": "anchor_source"}],
        },
    )

    run_render_stills(stage_input)

    assert "reference_image" not in calls[0]



def test_render_stills_generates_white_background_flux_tti_anchor_before_reference_keyframes(monkeypatch):
    calls = []

    def _fake_run_flux2_still(_config, item):
        calls.append(dict(item))
        return f"D:/renders/{item['shot_id']}.png"

    monkeypatch.setattr("ai_mv.core.stages.render_stills.run_flux2_still", _fake_run_flux2_still)
    stage_input = StageInput(
        run_id="run-anchor-package",
        config={"render": {"flux2_size": "1280x720"}},
        payload={
            "anchor_package": {
                "anchors": [
                    {
                        "anchor_id": "ANCHOR_CHARACTER_FULL_BODY",
                        "anchor_type": "character_full_body",
                        "material_class": "character_reference_anchor",
                        "workflow_target": "image_flux2_text_to_image",
                        "prompt_text": "single clean full-body identity reference card, pure white seamless background, no street",
                    }
                ],
                "variant_policy": {"workflow_target": "image_flux2_reference_image"},
            },
            "shot_plan": [{"shot_id": "S001", "visual_mode": "hero_medium"}],
            "render_plan": [
                {
                    "shot_id": "S001",
                    "still_prompt_text": "same lead woman in a rainy neon street keyframe",
                    "continuity_contract": {"protagonist_anchor": "same lead woman", "world_anchor": "same rainy neon street"},
                }
            ],
        },
    )

    out = run_render_stills(stage_input)

    assert [call["shot_id"] for call in calls] == ["ANCHOR_CHARACTER_FULL_BODY", "S001"]
    assert calls[0]["workflow_target"] == "image_flux2_text_to_image"
    assert "pure white seamless background" in calls[0]["positive_prompt"]
    assert "reference_image" not in calls[0]
    assert calls[1]["reference_image"] == "D:/renders/ANCHOR_CHARACTER_FULL_BODY.png"
    assert out.payload["anchor_results"] == [
        {
            "anchor_id": "ANCHOR_CHARACTER_FULL_BODY",
            "anchor_type": "character_full_body",
            "material_class": "character_reference_anchor",
            "workflow_target": "image_flux2_text_to_image",
            "image": "D:/renders/ANCHOR_CHARACTER_FULL_BODY.png",
            "prompt_text": "single clean full-body identity reference card, pure white seamless background, no street",
            "status": "done",
        }
    ]


def test_render_stills_uses_first_generated_anchor_still_for_later_continuity_shots(monkeypatch):
    calls = []

    def _fake_run_flux2_still(_config, item):
        calls.append(dict(item))
        return f"D:/renders/{item['shot_id']}.png"

    monkeypatch.setattr("ai_mv.core.stages.render_stills.run_flux2_still", _fake_run_flux2_still)
    stage_input = StageInput(
        run_id="run-anchor-reference",
        config={"render": {"flux2_size": "1280x720"}},
        payload={
            "shot_plan": [
                {"shot_id": "S001", "visual_mode": "street_establishing"},
                {"shot_id": "S002", "visual_mode": "hero_medium"},
                {"shot_id": "S003", "visual_mode": "connective_medium"},
            ],
            "render_plan": [
                {
                    "shot_id": "S001",
                    "still_prompt_text": "same lead woman under wet neon",
                    "continuity_contract": {"protagonist_anchor": "same lead woman", "world_anchor": "same wet neon boulevard"},
                },
                {
                    "shot_id": "S002",
                    "still_prompt_text": "same lead woman closer to camera",
                    "continuity_contract": {"protagonist_anchor": "same lead woman", "world_anchor": "same wet neon boulevard"},
                },
                {
                    "shot_id": "S003",
                    "still_prompt_text": "same lead woman turning into side light",
                    "continuity_contract": {"protagonist_anchor": "same lead woman", "world_anchor": "same wet neon boulevard"},
                },
            ],
        },
    )

    run_render_stills(stage_input)

    assert "reference_image" not in calls[0]
    assert calls[1]["reference_image"] == "D:/renders/S001.png"
    assert calls[2]["reference_image"] == "D:/renders/S001.png"



def test_render_stills_uses_generated_performance_anchor_source_for_later_performance_shot(monkeypatch):
    calls = []

    def _fake_run_flux2_still(_config, item):
        calls.append(dict(item))
        return f"D:/renders/{item['shot_id']}.png"

    monkeypatch.setattr("ai_mv.core.stages.render_stills.run_flux2_still", _fake_run_flux2_still)
    stage_input = StageInput(
        run_id="run-performance-anchor-reference",
        config={"render": {"flux2_size": "1280x720"}},
        payload={
            "shot_plan": [
                {"shot_id": "S010", "visual_mode": "chorus_performance"},
                {"shot_id": "S011", "visual_mode": "chorus_front_lights"},
            ],
            "render_plan": [
                {
                    "shot_id": "S010",
                    "still_prompt_text": "same lead performer on the same glossy performance-night stage",
                    "reference_mode": "performance_anchor_source",
                    "reference_source_shot_id": "S010",
                    "identity_lock_strength": "performance_anchor",
                    "continuity_contract": {"protagonist_anchor": "same lead performer", "world_anchor": "same glossy performance-night stage"},
                },
                {
                    "shot_id": "S011",
                    "still_prompt_text": "same lead performer under chorus front lights on the same glossy performance-night stage",
                    "reference_mode": "use_performance_anchor_still",
                    "reference_source_shot_id": "S010",
                    "identity_lock_strength": "performance_anchor",
                    "continuity_contract": {"protagonist_anchor": "same lead performer", "world_anchor": "same glossy performance-night stage"},
                },
            ],
        },
    )

    run_render_stills(stage_input)

    assert "reference_image" not in calls[0]
    assert calls[1]["reference_image"] == "D:/renders/S010.png"



def test_render_stills_prefers_generated_performance_anchor_over_earlier_intro_anchor(monkeypatch):
    calls = []

    def _fake_run_flux2_still(_config, item):
        calls.append(dict(item))
        return f"D:/renders/{item['shot_id']}.png"

    monkeypatch.setattr("ai_mv.core.stages.render_stills.run_flux2_still", _fake_run_flux2_still)
    stage_input = StageInput(
        run_id="run-performance-anchor-priority",
        config={"render": {"flux2_size": "1280x720"}},
        payload={
            "shot_plan": [
                {"shot_id": "S001", "visual_mode": "street_establishing"},
                {"shot_id": "S010", "visual_mode": "chorus_performance"},
                {"shot_id": "S011", "visual_mode": "chorus_front_lights"},
            ],
            "render_plan": [
                {
                    "shot_id": "S001",
                    "still_prompt_text": "same lead woman under wet neon",
                    "reference_mode": "anchor_source",
                    "reference_source_shot_id": "S001",
                    "continuity_contract": {"protagonist_anchor": "same lead woman", "world_anchor": "same wet neon boulevard"},
                },
                {
                    "shot_id": "S010",
                    "still_prompt_text": "same lead performer on the same glossy performance-night stage",
                    "reference_mode": "performance_anchor_source",
                    "reference_source_shot_id": "S010",
                    "identity_lock_strength": "performance_anchor",
                    "continuity_contract": {"protagonist_anchor": "same lead performer", "world_anchor": "same glossy performance-night stage"},
                },
                {
                    "shot_id": "S011",
                    "still_prompt_text": "same lead performer under chorus front lights on the same glossy performance-night stage",
                    "reference_mode": "use_performance_anchor_still",
                    "reference_source_shot_id": "",
                    "identity_lock_strength": "performance_anchor",
                    "continuity_contract": {"protagonist_anchor": "same lead performer", "world_anchor": "same glossy performance-night stage"},
                },
            ],
        },
    )

    run_render_stills(stage_input)

    assert calls[2]["reference_image"] == "D:/renders/S010.png"



def test_render_stills_does_not_fallback_to_intro_anchor_when_performance_anchor_is_missing(monkeypatch):
    calls = []

    def _fake_run_flux2_still(_config, item):
        calls.append(dict(item))
        return f"D:/renders/{item['shot_id']}.png"

    monkeypatch.setattr("ai_mv.core.stages.render_stills.run_flux2_still", _fake_run_flux2_still)
    stage_input = StageInput(
        run_id="run-performance-anchor-missing",
        config={"render": {"flux2_size": "1280x720"}},
        payload={
            "shot_plan": [
                {"shot_id": "S001", "visual_mode": "street_establishing"},
                {"shot_id": "S011", "visual_mode": "chorus_front_lights"},
            ],
            "render_plan": [
                {
                    "shot_id": "S001",
                    "still_prompt_text": "same lead woman under wet neon",
                    "reference_mode": "anchor_source",
                    "reference_source_shot_id": "S001",
                    "continuity_contract": {"protagonist_anchor": "same lead woman", "world_anchor": "same wet neon boulevard"},
                },
                {
                    "shot_id": "S011",
                    "still_prompt_text": "same lead performer under chorus front lights on the same glossy performance-night stage",
                    "reference_mode": "use_performance_anchor_still",
                    "reference_source_shot_id": "",
                    "identity_lock_strength": "performance_anchor",
                    "continuity_contract": {"protagonist_anchor": "same lead performer", "world_anchor": "same glossy performance-night stage"},
                },
            ],
        },
    )

    run_render_stills(stage_input)

    assert "reference_image" not in calls[1]


def test_render_stills_adds_single_keyframe_constraints_to_prompt(monkeypatch):
    calls = []

    def _fake_run_flux2_still(_config, item):
        calls.append(item)
        return f"D:/renders/{item['shot_id']}.png"

    monkeypatch.setattr("ai_mv.core.stages.render_stills.run_flux2_still", _fake_run_flux2_still)
    stage_input = StageInput(
        run_id="run-1b",
        config={"render": {"flux2_size": "1024x1024"}},
        payload={
            "shot_plan": [{"shot_id": "S009"}],
            "render_plan": [{"shot_id": "S009", "prompt_polish": "night station portrait, reflective glass, film grain"}],
        },
    )

    run_render_stills(stage_input)

    prompt = calls[0]["positive_prompt"]
    assert "night station portrait, reflective glass, film grain" in prompt
    assert "photoreal live-action still frame" in prompt
    assert "single cinematic keyframe" in prompt
    assert "subject integrated into the environment" in prompt
    assert "close-up portrait integrated into the environment" not in prompt
    assert "no inset portrait" in prompt
    assert "cinematic still image" not in prompt


def test_single_keyframe_prompt_text_uses_subject_level_environment_constraint():
    prompt = _single_keyframe_prompt_text("A young woman walking through a neon street.")

    assert "subject integrated into the environment" in prompt
    assert "close-up portrait integrated into the environment" not in prompt
    assert "photoreal live-action still frame" in prompt
    assert "cinematic still image" not in prompt


def test_render_stills_constrained_wider_body_case_uses_soft_single_scene_variant(monkeypatch):
    calls = []

    def _fake_run_flux2_still(_config, item):
        calls.append(item)
        return f"D:/renders/{item['shot_id']}.png"

    monkeypatch.setattr("ai_mv.core.stages.render_stills.run_flux2_still", _fake_run_flux2_still)
    stage_input = StageInput(
        run_id="run-wide-constrained",
        config={"render": {"flux2_size": "1280x720"}},
        payload={
            "shot_plan": [{"shot_id": "S009B", "visual_mode": "night_drive"}],
            "render_plan": [{"shot_id": "S009B", "still_constraint_mode": "constrained", "still_prompt_text": "A young woman in an oversized varsity jacket walking through a neon side street with wet pavement reflections and convenience-store glow. Keep one continuous medium-wide frame with clear full-body readability."}],
        },
    )

    run_render_stills(stage_input)

    prompt = calls[0]["positive_prompt"]
    assert "Render it as one clean photoreal live-action still frame in a single continuous scene" in prompt
    assert "subject integrated into the environment" in prompt
    assert "no inset portrait" not in prompt
    assert "close-up portrait integrated into the environment" not in prompt


def test_render_stills_keeps_window_reflection_case_raw(monkeypatch):
    calls = []

    def _fake_run_flux2_still(_config, item):
        calls.append(item)
        return f"D:/renders/{item['shot_id']}.png"

    monkeypatch.setattr("ai_mv.core.stages.render_stills.run_flux2_still", _fake_run_flux2_still)
    stage_input = StageInput(
        run_id="run-window-raw",
        config={"render": {"flux2_size": "1280x720"}},
        payload={
            "shot_plan": [{"shot_id": "S020", "visual_mode": "window_reflection"}],
            "render_plan": [{"shot_id": "S020", "still_prompt_text": "A young woman leans by a train window while city neon reflects across the glass in a quiet late-night transit interior, as one continuous medium close-up."}],
        },
    )

    run_render_stills(stage_input)

    prompt = calls[0]["positive_prompt"]
    assert "single cinematic keyframe" not in prompt
    assert "one uninterrupted composition" not in prompt
    assert prompt.startswith("A young woman leans by a train window")


def test_render_stills_keeps_readability_repair_prompt_raw(monkeypatch):
    calls = []

    def _fake_run_flux2_still(_config, item):
        calls.append(item)
        return f"D:/renders/{item['shot_id']}.png"

    monkeypatch.setattr("ai_mv.core.stages.render_stills.run_flux2_still", _fake_run_flux2_still)
    stage_input = StageInput(
        run_id="run-repair-raw",
        config={"render": {"flux2_size": "1280x720"}},
        payload={
            "shot_plan": [{"shot_id": "S021", "visual_mode": "night_drive"}],
            "render_plan": [{"shot_id": "S021", "still_prompt_text": "The same young woman in the same satin bomber jacket under station light in the same late-night city world. Keep one readable medium shot with clear face visibility, visible upper-body framing, restrained neon reflection, and motion-safe continuity."}],
        },
    )

    run_render_stills(stage_input)

    prompt = calls[0]["positive_prompt"]
    assert "single cinematic keyframe" not in prompt
    assert "one uninterrupted composition" not in prompt
    assert "clear face visibility" in prompt


def test_render_stills_defaults_standard_case_to_constrained(monkeypatch):
    calls = []

    def _fake_run_flux2_still(_config, item):
        calls.append(item)
        return f"D:/renders/{item['shot_id']}.png"

    monkeypatch.setattr("ai_mv.core.stages.render_stills.run_flux2_still", _fake_run_flux2_still)
    stage_input = StageInput(
        run_id="run-default-constrained",
        config={"render": {"flux2_size": "1280x720"}},
        payload={
            "shot_plan": [{"shot_id": "S022", "visual_mode": "night_drive"}],
            "render_plan": [{"shot_id": "S022", "still_prompt_text": "A young woman driving through the city at night with dashboard glow across her face and passing streetlight reflections."}],
        },
    )

    run_render_stills(stage_input)

    prompt = calls[0]["positive_prompt"]
    assert "single cinematic keyframe" in prompt
    assert "one uninterrupted composition" in prompt


def test_render_stills_allows_explicit_raw_override(monkeypatch):
    calls = []

    def _fake_run_flux2_still(_config, item):
        calls.append(item)
        return f"D:/renders/{item['shot_id']}.png"

    monkeypatch.setattr("ai_mv.core.stages.render_stills.run_flux2_still", _fake_run_flux2_still)
    stage_input = StageInput(
        run_id="run-explicit-raw",
        config={"render": {"flux2_size": "1280x720"}},
        payload={
            "shot_plan": [{"shot_id": "S023", "visual_mode": "night_drive"}],
            "render_plan": [{"shot_id": "S023", "still_constraint_mode": "raw", "still_prompt_text": "A young woman in the same late-night city world framed in a readable medium shot with restrained reflections."}],
        },
    )

    run_render_stills(stage_input)

    prompt = calls[0]["positive_prompt"]
    assert "single cinematic keyframe" not in prompt
    assert prompt.startswith("A young woman in the same late-night city world")


def test_render_stills_allows_explicit_constrained_override(monkeypatch):
    calls = []

    def _fake_run_flux2_still(_config, item):
        calls.append(item)
        return f"D:/renders/{item['shot_id']}.png"

    monkeypatch.setattr("ai_mv.core.stages.render_stills.run_flux2_still", _fake_run_flux2_still)
    stage_input = StageInput(
        run_id="run-explicit-constrained",
        config={"render": {"flux2_size": "1280x720"}},
        payload={
            "shot_plan": [{"shot_id": "S024", "visual_mode": "window_reflection"}],
            "render_plan": [{"shot_id": "S024", "still_constraint_mode": "constrained", "still_prompt_text": "A young woman seen through side glass with layered city reflections in one reflective late-night transit moment."}],
        },
    )

    run_render_stills(stage_input)

    prompt = calls[0]["positive_prompt"]
    assert "single cinematic keyframe" in prompt
    assert "one uninterrupted composition" in prompt


def test_render_stills_strips_panel_prone_graphic_prompt_tokens(monkeypatch):
    calls = []

    def _fake_run_flux2_still(_config, item):
        calls.append(item)
        return f"D:/renders/{item['shot_id']}.png"

    monkeypatch.setattr("ai_mv.core.stages.render_stills.run_flux2_still", _fake_run_flux2_still)
    stage_input = StageInput(
        run_id="run-1c",
        config={"render": {"flux2_size": "1280x720"}},
        payload={
            "shot_plan": [{"shot_id": "S010"}],
            "render_plan": [
                {
                    "shot_id": "S010",
                    "prompt_polish": "night station portrait, bold graphic composition, graphic reflective close-up styling, reflective glass, film grain",
                }
            ],
        },
    )

    run_render_stills(stage_input)

    prompt = calls[0]["positive_prompt"]
    assert "night station portrait" in prompt
    assert "reflective glass" in prompt
    assert "film grain" in prompt
    assert "bold graphic composition" not in prompt
    assert "graphic reflective close-up styling" not in prompt
    assert "full-bleed frame" in prompt


def test_render_stills_strips_storyboard_like_meta_prompt_tokens(monkeypatch):
    calls = []

    def _fake_run_flux2_still(_config, item):
        calls.append(item)
        return f"D:/renders/{item['shot_id']}.png"

    monkeypatch.setattr("ai_mv.core.stages.render_stills.run_flux2_still", _fake_run_flux2_still)
    stage_input = StageInput(
        run_id="run-1d",
        config={"render": {"flux2_size": "1280x720"}},
        payload={
            "shot_plan": [{"shot_id": "S011"}],
            "render_plan": [
                {
                    "shot_id": "S011",
                    "prompt_polish": "Japanese 80s city pop music video, progression: opening pass through the night, scene event: late-night city movement, a close-up of a singer in reflected night light, film grain",
                }
            ],
        },
    )

    run_render_stills(stage_input)

    prompt = calls[0]["positive_prompt"]
    assert "a close-up of a singer in reflected night light" in prompt
    assert "film grain" in prompt
    assert "Japanese 80s city pop music video" not in prompt
    assert "progression: opening pass through the night" not in prompt
    assert "scene event: late-night city movement" not in prompt


def test_render_stills_uses_reference_image_when_rerender_source_exists(monkeypatch):
    calls = []

    def _fake_run_flux2_still(_config, item):
        calls.append(item)
        return f"D:/renders/{item['shot_id']}.png"

    monkeypatch.setattr("ai_mv.core.stages.render_stills.run_flux2_still", _fake_run_flux2_still)
    stage_input = StageInput(
        run_id="run-1e",
        config={"render": {"flux2_size": "1280x720"}},
        payload={
            "shot_plan": [{"shot_id": "S012"}],
            "render_plan": [{"shot_id": "S012", "still_prompt_text": "same protagonist under station light", "reference_mode": "reuse_prior_still"}],
            "still_results": [{"shot_id": "S012", "image": "D:/renders/prev_S012.png"}],
        },
    )

    run_render_stills(stage_input)

    assert calls[0]["reference_image"] == "D:/renders/prev_S012.png"


def test_plan_preview_builds_flux2_style_prompt_tokens():
    from ai_mv.core.stages.plan_mv import build_plan_preview_payload

    payload = build_plan_preview_payload(
        {"planning": {"max_shot_sec": 8.0}},
        {
            "concept_text": "Japanese 80s city pop",
            "audio_map": {
                "duration_sec": 32.0,
                "sections": [
                    {"label": "Intro", "name": "intro", "start_sec": 0.0, "end_sec": 8.0},
                    {"label": "Verse 1", "name": "verse_1", "start_sec": 8.0, "end_sec": 16.0},
                    {"label": "Chorus", "name": "chorus", "start_sec": 16.0, "end_sec": 24.0},
                    {"label": "Outro", "name": "outro", "start_sec": 24.0, "end_sec": 32.0},
                ],
            },
        },
    )

    prompt = payload["render_plan"][0]["prompt_polish"]
    assert "cinematic live-action lighting" in prompt
    assert "same protagonist" in prompt
    assert "motion-safe keyframe" in prompt
    assert "80s japanese city pop illustration" not in prompt
    assert "film grain" in prompt


def test_render_clips_routes_ia2v(monkeypatch):
    calls = []

    def _fake_run_ltx_ia2v(_config, item):
        calls.append(("ia2v", item))
        return f"D:/renders/{item['shot_id']}_ia2v.mp4"

    monkeypatch.setattr("ai_mv.core.stages.render_clips.run_ltx_ia2v", _fake_run_ltx_ia2v)
    stage_input = StageInput(
        run_id="run-2",
        config={"render": {"ltx_negative": "bad", "ltx_fps": 24, "ltx_default_shot_sec": 4.0}},
        payload={
            "music_file": "music/song.mp3",
            "shot_plan": [{"shot_id": "S001", "duration_sec": 5.0, "render_mode": "ia2v", "material_id": "MAT_001", "section_id": "SEC_001", "start_sec": 0.0}],
            "render_plan": [
                {
                    "shot_id": "S001",
                    "render_mode": "ia2v",
                    "material_id": "MAT_001",
                    "section_id": "SEC_001",
                    "prompt_seed": "night drive",
                    "clip_prompt_seed": "slow windshield drift",
                    "clip_positive_prompt": "slow windshield drift, stable motion, no abrupt pose change",
                }
            ],
            "still_results": [{"shot_id": "S001", "image": "D:/renders/S001.png", "material_id": "MAT_001", "section_id": "SEC_001"}],
        },
    )

    out = run_render_clips(stage_input)

    assert out.payload["clip_results"][0]["video"] == "D:/renders/S001_ia2v.mp4"
    assert out.payload["clip_results"][0]["material_id"] == "MAT_001"
    assert out.payload["clip_results"][0]["section_id"] == "SEC_001"
    assert calls[0][1]["image"] == "D:/renders/S001.png"
    assert calls[0][1]["filename_prefix"] == "ai_mv/runs/run-2/clips/shot-S001-ia2v"
    assert calls[0][1]["prompt_seed"] == "slow windshield drift"
    assert calls[0][1]["positive_prompt"] == "slow windshield drift, stable motion, no abrupt pose change"
    assert calls[0][1]["audio"] == "music/song.mp3"


def test_render_clips_requires_explicit_render_mode_in_canonical_runtime():
    stage_input = StageInput(
        run_id="run-2-missing-mode",
        config={"render": {"ltx_negative": "bad", "ltx_fps": 24, "ltx_default_shot_sec": 4.0}},
        payload={
            "music_file": "music/song.mp3",
            "shot_plan": [{"shot_id": "S001", "duration_sec": 5.0}],
            "render_plan": [{"shot_id": "S001", "prompt_seed": "night drive"}],
            "still_results": [{"shot_id": "S001", "image": "D:/renders/S001.png"}],
        },
    )

    import pytest

    with pytest.raises(RuntimeError, match="missing render_mode for shot: S001"):
        run_render_clips(stage_input)


def test_render_clips_fails_fast_when_ia2v_still_is_missing():
    stage_input = StageInput(
        run_id="run-2-missing-still",
        config={"render": {"ltx_negative": "bad", "ltx_fps": 24, "ltx_default_shot_sec": 4.0}},
        payload={
            "music_file": "music/song.mp3",
            "shot_plan": [{"shot_id": "S001", "duration_sec": 5.0, "render_mode": "ia2v", "start_sec": 0.0}],
            "render_plan": [{"shot_id": "S001", "render_mode": "ia2v", "prompt_seed": "night drive"}],
            "still_results": [],
        },
    )

    import pytest

    with pytest.raises(RuntimeError, match="missing source still for shot: S001"):
        run_render_clips(stage_input)


def test_render_clips_fails_fast_when_ia2v_music_file_is_missing():
    stage_input = StageInput(
        run_id="run-2-missing-audio",
        config={"render": {"ltx_negative": "bad", "ltx_fps": 24, "ltx_default_shot_sec": 4.0}},
        payload={
            "music_file": "",
            "shot_plan": [{"shot_id": "S001", "duration_sec": 5.0, "render_mode": "ia2v", "start_sec": 0.0}],
            "render_plan": [{"shot_id": "S001", "render_mode": "ia2v", "prompt_seed": "night drive"}],
            "still_results": [{"shot_id": "S001", "image": "D:/renders/S001.png"}],
        },
    )

    import pytest

    with pytest.raises(RuntimeError, match="missing music file for ia2v shot: S001"):
        run_render_clips(stage_input)


def test_render_clips_rejects_unsupported_legacy_mode():
    stage_input = StageInput(
        run_id="run-2-unsupported-mode",
        config={"render": {"ltx_negative": "bad", "ltx_fps": 24, "ltx_default_shot_sec": 4.0}},
        payload={
            "music_file": "music/song.mp3",
            "shot_plan": [
                {"shot_id": "S003", "duration_sec": 4.0, "render_mode": "deprecated_mode"},
                {"shot_id": "S004", "duration_sec": 4.0, "render_mode": "ia2v", "start_sec": 4.0},
            ],
            "render_plan": [
                {"shot_id": "S003", "render_mode": "deprecated_mode", "prompt_seed": "bridge move"},
                {"shot_id": "S004", "render_mode": "ia2v", "prompt_seed": "chorus hold"},
            ],
            "still_results": [
                {"shot_id": "S003", "image": "D:/renders/S003.png"},
                {"shot_id": "S004", "image": "D:/renders/S004.png"},
            ],
        },
    )

    import pytest

    with pytest.raises(RuntimeError, match="unsupported render_mode for shot S003: deprecated_mode"):
        run_render_clips(stage_input)


def test_review_outputs_propagates_assembly_quality_summary_from_review_inputs(monkeypatch):
    monkeypatch.setattr("ai_mv.core.stages.review_stage.file_exists", lambda _path: True)
    monkeypatch.setattr("ai_mv.core.stages.review_outputs.ffprobe_duration", lambda _path: 10.0)

    stage_input = StageInput(
        run_id="run-review-assembly-quality",
        config={"review": {"max_audio_video_drift_sec": 0.5}},
        payload={
            "final_video": "D:/renders/final.mp4",
            "music_file": "D:/renders/song.mp3",
            "shot_plan": [{"shot_id": "S001"}, {"shot_id": "S002"}, {"shot_id": "S003"}],
            "still_results": [
                {"shot_id": "S001", "image": "D:/renders/S001.png", "status": "done"},
                {"shot_id": "S002", "image": "D:/renders/S002.png", "status": "done"},
                {"shot_id": "S003", "image": "D:/renders/S003.png", "status": "done"},
            ],
            "clip_results": [
                {"shot_id": "S001", "video": "D:/renders/S001.mp4", "status": "done"},
                {"shot_id": "S002", "video": "D:/renders/S002.mp4", "status": "done"},
                {"shot_id": "S003", "video": "D:/renders/S003.mp4", "status": "done"},
            ],
            "review_inputs": {
                "music_file": "D:/renders/song.mp3",
                "edit_intent_by_shot": {
                    "S001": {"edit_priority": "high", "section_emphasis": "chorus_push", "transition_in": "accent_in", "transition_out": "accent_out"},
                    "S002": {"edit_priority": "medium", "section_emphasis": "sequence_support", "transition_in": "cut_in", "transition_out": "cut_out"},
                    "S003": {"edit_priority": "medium", "section_emphasis": "bridge_contrast", "transition_in": "glide_in", "transition_out": "handoff_out"},
                },
                "render_count_by_shot": {"S001": 3, "S002": 1, "S003": 2},
                "render_priority_by_shot": {"S001": 0.9, "S002": 0.6, "S003": 0.78},
                "render_planning_by_shot": {
                    "S001": {"mode_importance_score": 1.0, "section_emphasis_score": 1.0},
                    "S002": {"mode_importance_score": 0.68, "section_emphasis_score": 0.6},
                    "S003": {"mode_importance_score": 0.85, "section_emphasis_score": 0.78},
                },
            },
        },
    )

    out = run_review_outputs(stage_input)

    summary = out.payload["review_report"]["assembly_quality_summary"]
    assert summary["chorus_emphasis_score"] == 0.9
    assert summary["slideshow_risk_score"] == 0.13
    assert summary["transition_intentionality_score"] == 0.67
    assert summary["chorus_emphasis_within_threshold"] is True
    assert summary["slideshow_risk_within_threshold"] is True
    assert "cadence_variety_score" not in summary
    assert "snap_variety_score" not in summary



def test_review_outputs_ignores_malformed_render_planning_metadata(monkeypatch):
    monkeypatch.setattr("ai_mv.core.stages.review_stage.file_exists", lambda _path: True)
    monkeypatch.setattr("ai_mv.core.stages.review_outputs.ffprobe_duration", lambda _path: 10.0)

    stage_input = StageInput(
        run_id="run-review-assembly-quality-malformed",
        config={"review": {"max_audio_video_drift_sec": 0.5}},
        payload={
            "final_video": "D:/renders/final.mp4",
            "music_file": "D:/renders/song.mp3",
            "shot_plan": [{"shot_id": "S001"}],
            "still_results": [{"shot_id": "S001", "image": "D:/renders/S001.png", "status": "done"}],
            "clip_results": [{"shot_id": "S001", "video": "D:/renders/S001.mp4", "status": "done"}],
            "review_inputs": {
                "music_file": "D:/renders/song.mp3",
                "edit_intent_by_shot": {
                    "S001": {"edit_priority": "high", "section_emphasis": "chorus_push", "transition_in": "accent_in", "transition_out": "accent_out"},
                },
                "render_count_by_shot": {"S001": 2},
                "render_priority_by_shot": {"S001": 0.9},
                "render_planning_by_shot": {"S001": 5},
            },
        },
    )

    out = run_review_outputs(stage_input)

    assert out.payload["review_report"]["assembly_quality_summary"]["chorus_emphasis_score"] == 0.48
    assert out.payload["review_report"]["assembly_quality_summary"]["slideshow_risk_within_threshold"] is True



def test_review_outputs_sanitizes_non_finite_numeric_metadata(monkeypatch):
    monkeypatch.setattr("ai_mv.core.stages.review_stage.file_exists", lambda _path: True)
    monkeypatch.setattr("ai_mv.core.stages.review_outputs.ffprobe_duration", lambda _path: 10.0)

    stage_input = StageInput(
        run_id="run-review-assembly-quality-nonfinite",
        config={"review": {"max_audio_video_drift_sec": 0.5}},
        payload={
            "final_video": "D:/renders/final.mp4",
            "music_file": "D:/renders/song.mp3",
            "shot_plan": [{"shot_id": "S001"}],
            "still_results": [{"shot_id": "S001", "image": "D:/renders/S001.png", "status": "done"}],
            "clip_results": [{"shot_id": "S001", "video": "D:/renders/S001.mp4", "status": "done"}],
            "review_inputs": {
                "music_file": "D:/renders/song.mp3",
                "edit_intent_by_shot": {
                    "S001": {"edit_priority": "high", "section_emphasis": "chorus_push", "transition_in": "accent_in", "transition_out": "accent_out"},
                },
                "render_count_by_shot": {"S001": "inf"},
                "render_priority_by_shot": {"S001": "nan"},
                "render_planning_by_shot": {"S001": {"mode_importance_score": "nan"}},
            },
        },
    )

    out = run_review_outputs(stage_input)

    summary = out.payload["review_report"]["assembly_quality_summary"]
    assert summary["chorus_emphasis_score"] == 0.0
    assert summary["slideshow_risk_score"] == 0.33
    assert summary["transition_intentionality_score"] == 1.0
    assert summary["chorus_emphasis_within_threshold"] is False
    assert summary["slideshow_risk_within_threshold"] is True
    assert "cadence_variety_score" not in summary
    assert "snap_variety_score" not in summary



def test_assemble_mv_runs_ffmpeg(monkeypatch, tmp_path):
    final_file = tmp_path / "ComfyUI" / "output" / "ai_mv" / "runs" / "run-3" / "final" / "mv.mp4"
    calls = {}

    def _fake_final_video_path(_config, run_id, scope="run"):
        assert run_id == "run-3"
        assert scope == "run"
        final_file.parent.mkdir(parents=True, exist_ok=True)
        return final_file

    def _fake_resolve_generated_file(_config, ref, _exts, _label):
        return Path(ref)

    def _fake_run_ffmpeg_mux(clips, audio, out, _config):
        calls["clips"] = clips
        calls["audio"] = audio
        calls["out"] = out
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b"video")
        return True

    monkeypatch.setattr("ai_mv.core.stages.assemble_mv.final_video_path", _fake_final_video_path)
    monkeypatch.setattr("ai_mv.core.stages.assemble_mv.resolve_generated_file", _fake_resolve_generated_file)
    monkeypatch.setattr("ai_mv.core.stages.assemble_mv.run_ffmpeg_mux", _fake_run_ffmpeg_mux)
    stage_input = StageInput(
        run_id="run-3",
        config={"video": {"target": "1920x1080@24"}},
        payload={
            "music_file": str(tmp_path / "music.mp3"),
            "clip_results": [{"shot_id": "S001", "video": str(tmp_path / "clip.mp4")}],
        },
    )

    out = run_assemble_mv(stage_input)

    assert out.payload["final_video"] == str(final_file)
    assert calls["out"] == final_file
    assert len(calls["clips"]) == 1


def test_assemble_mv_propagates_review_quality_findings_path_from_config(monkeypatch, tmp_path):
    final_file = tmp_path / "ComfyUI" / "output" / "ai_mv" / "runs" / "run-3b" / "final" / "mv.mp4"
    findings_path = tmp_path / "manual-review" / "review-findings.json"

    def _fake_final_video_path(_config, run_id, scope="run"):
        assert run_id == "run-3b"
        assert scope == "run"
        final_file.parent.mkdir(parents=True, exist_ok=True)
        return final_file

    def _fake_resolve_generated_file(_config, ref, _exts, _label):
        return Path(ref)

    def _fake_run_ffmpeg_mux(clips, audio, out, _config):
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b"video")
        return True

    monkeypatch.setattr("ai_mv.core.stages.assemble_mv.final_video_path", _fake_final_video_path)
    monkeypatch.setattr("ai_mv.core.stages.assemble_mv.resolve_generated_file", _fake_resolve_generated_file)
    monkeypatch.setattr("ai_mv.core.stages.assemble_mv.run_ffmpeg_mux", _fake_run_ffmpeg_mux)
    stage_input = StageInput(
        run_id="run-3b",
        config={"review": {"quality_findings_path": str(findings_path)}},
        payload={
            "music_file": str(tmp_path / "music.mp3"),
            "clip_results": [{"shot_id": "S001", "video": str(tmp_path / "clip.mp4")}],
        },
    )

    out = run_assemble_mv(stage_input)

    assert out.payload["review_inputs"]["quality_findings_path"] == str(findings_path)


def test_assemble_mv_propagates_audio_review_rubric_path_from_config(monkeypatch, tmp_path):
    final_file = tmp_path / "ComfyUI" / "output" / "ai_mv" / "runs" / "run-3c" / "final" / "mv.mp4"
    rubric_path = tmp_path / "manual-review" / "audio-review-rubric.json"

    def _fake_final_video_path(_config, run_id, scope="run"):
        assert run_id == "run-3c"
        assert scope == "run"
        final_file.parent.mkdir(parents=True, exist_ok=True)
        return final_file

    def _fake_resolve_generated_file(_config, ref, _exts, _label):
        return Path(ref)

    def _fake_run_ffmpeg_mux(clips, audio, out, _config):
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b"video")
        return True

    monkeypatch.setattr("ai_mv.core.stages.assemble_mv.final_video_path", _fake_final_video_path)
    monkeypatch.setattr("ai_mv.core.stages.assemble_mv.resolve_generated_file", _fake_resolve_generated_file)
    monkeypatch.setattr("ai_mv.core.stages.assemble_mv.run_ffmpeg_mux", _fake_run_ffmpeg_mux)
    stage_input = StageInput(
        run_id="run-3c",
        config={"review": {"audio_review_rubric_path": str(rubric_path)}},
        payload={
            "music_file": str(tmp_path / "music.mp3"),
            "clip_results": [{"shot_id": "S001", "video": str(tmp_path / "clip.mp4")}],
        },
    )

    out = run_assemble_mv(stage_input)

    assert out.payload["review_inputs"]["audio_review_rubric_path"] == str(rubric_path)


def test_review_outputs_marks_done_when_final_exists():
    final_path = Path("D:/renders/final.mp4")
    existing = {str(final_path), "D:/renders/S001.png", "D:/renders/S001.mp4"}

    def _fake_exists(self):
        return str(self).replace("\\", "/") in {path.replace("\\", "/") for path in existing}

    from pathlib import Path as _Path

    _original_exists = _Path.exists
    _Path.exists = _fake_exists
    try:
        stage_input = StageInput(
            run_id="run-4",
            config={},
            payload={
                "final_video": str(final_path),
                "shot_plan": [{"shot_id": "S001"}],
                "still_results": [{"shot_id": "S001", "image": "D:/renders/S001.png", "status": "done"}],
                "clip_results": [{"shot_id": "S001", "video": "D:/renders/S001.mp4", "status": "done"}],
            },
        )

        out = run_review_outputs(stage_input)

        assert out.payload["review_report"]["status"] == "done"
        assert out.payload["review_report"]["completed_counts"]["clips"] == 1
        assert out.payload["review_report"]["rerender_targets"] == []
    finally:
        _Path.exists = _original_exists


def test_review_outputs_marks_missing_assets_for_rerender():
    stage_input = StageInput(
        run_id="run-5",
        config={},
        payload={
            "final_video": "D:/renders/final.mp4",
            "shot_plan": [{"shot_id": "S001"}, {"shot_id": "S002"}],
            "still_results": [
                {"shot_id": "S001", "image": "D:/renders/S001.png", "status": "done"},
                {"shot_id": "S002", "image": "", "status": "failed"},
            ],
            "clip_results": [
                {"shot_id": "S001", "video": "", "status": "failed"},
                {"shot_id": "S002", "video": "D:/renders/S002.mp4", "status": "done"},
            ],
        },
    )

    out = run_review_outputs(stage_input)

    assert out.payload["review_report"]["status"] == "needs_rerender"
    assert sorted(out.payload["review_report"]["rerender_targets"]) == ["S001", "S002"]
    assert out.payload["review_report"]["blocking_checks"]["all_clips_rendered"] is False


def test_review_outputs_marks_policy_red_risk_duration_overrun_for_rerender(monkeypatch):
    monkeypatch.setattr("ai_mv.core.stages.review_stage.file_exists", lambda _path: True)
    monkeypatch.setattr("ai_mv.core.review.policy.file_exists", lambda _path: True)
    monkeypatch.setattr("ai_mv.core.stages.review_outputs.ffprobe_duration", lambda _path: 10.0)
    stage_input = StageInput(
        run_id="run-policy-risk",
        config={"review": {"max_audio_video_drift_sec": 0.5}},
        payload={
            "final_video": "D:/renders/final.mp4",
            "music_file": "D:/renders/song.mp3",
            "shot_plan": [{"shot_id": "S001", "material_id": "MAT_001", "section_id": "SEC_CHORUS"}],
            "material_plan": [{"material_id": "MAT_001", "section_id": "SEC_CHORUS"}],
            "render_plan": [
                {
                    "shot_id": "S001",
                    "material_id": "MAT_001",
                    "section_id": "SEC_CHORUS",
                    "production_policy": {
                        "candidate_role": "high_risk_interaction_payoff",
                        "ia2v_risk_class": "red",
                        "recommended_duration_sec": {"min": 0.3, "max": 0.7},
                    },
                }
            ],
            "still_results": [{"shot_id": "S001", "image": "D:/renders/S001.png", "status": "done"}],
            "clip_results": [{"shot_id": "S001", "video": "D:/renders/S001.mp4", "status": "done"}],
            "review_inputs": {
                "production_policy_by_shot": {
                    "S001": {
                        "candidate_role": "high_risk_interaction_payoff",
                        "ia2v_risk_class": "red",
                        "recommended_duration_sec": {"min": 0.3, "max": 0.7},
                    }
                },
                "trimmed_coverage_by_shot": {"S001": 1.4},
            },
        },
    )

    out = run_review_outputs(stage_input)

    report = out.payload["review_report"]
    assert report["status"] == "needs_rerender"
    assert report["rerender_reasons"] == {"S001": ["red_risk_clip_held_too_long"]}
    assert report["publishability_summary"]["final_mv_publishability"]["next_action"] == "revise_transition_selection"



def test_review_outputs_counts_latest_success_per_shot(monkeypatch):
    existing = {"D:/renders/final.mp4", "D:/renders/S001_retry.png", "D:/renders/S001_retry.mp4"}

    def _fake_exists(self):
        return str(self).replace("\\", "/") in {path.replace("\\", "/") for path in existing}

    from pathlib import Path as _Path

    _original_exists = _Path.exists
    _Path.exists = _fake_exists
    try:
        stage_input = StageInput(
            run_id="run-6",
            config={},
            payload={
                "final_video": "D:/renders/final.mp4",
                "shot_plan": [{"shot_id": "S001"}],
                "still_results": [
                    {"shot_id": "S001", "image": "", "status": "failed"},
                    {"shot_id": "S001", "image": "D:/renders/S001_retry.png", "status": "done"},
                ],
                "clip_results": [
                    {"shot_id": "S001", "video": "", "status": "failed"},
                    {"shot_id": "S001", "video": "D:/renders/S001_retry.mp4", "status": "done"},
                ],
            },
        )

        out = run_review_outputs(stage_input)

        assert out.payload["review_report"]["status"] == "done"
        assert out.payload["review_report"]["completed_counts"]["stills"] == 1
        assert out.payload["review_report"]["completed_counts"]["clips"] == 1
        assert out.payload["review_report"]["rerender_targets"] == []
    finally:
        _Path.exists = _original_exists


def test_review_outputs_marks_missing_result_rows_for_rerender():
    stage_input = StageInput(
        run_id="run-7",
        config={"review": {"max_rerender_targets": 3}},
        payload={
            "final_video": "D:/renders/final.mp4",
            "shot_plan": [{"shot_id": "S001"}, {"shot_id": "S002"}],
            "still_results": [{"shot_id": "S001", "image": "D:/renders/S001.png", "status": "done"}],
            "clip_results": [{"shot_id": "S001", "video": "D:/renders/S001.mp4", "status": "done"}],
        },
    )

    out = run_review_outputs(stage_input)

    assert out.payload["review_report"]["status"] == "needs_rerender"
    assert out.payload["review_report"]["rerender_targets"] == ["S001", "S002"]


def test_review_outputs_computes_audio_video_drift(monkeypatch):
    existing = {"D:/renders/final.mp4", "D:/renders/song.mp3", "D:/renders/S001.png", "D:/renders/S001.mp4"}

    def _fake_exists(self):
        return str(self).replace("\\", "/") in {path.replace("\\", "/") for path in existing}

    from pathlib import Path as _Path

    _original_exists = _Path.exists
    _Path.exists = _fake_exists
    monkeypatch.setattr("ai_mv.core.stages.review_outputs.ffprobe_duration", lambda path: 10.0 if str(path).endswith(".mp3") else 10.35)
    try:
        stage_input = StageInput(
            run_id="run-8",
            config={},
            payload={
                "music_file": "D:/renders/song.mp3",
                "final_video": "D:/renders/final.mp4",
                "shot_plan": [{"shot_id": "S001"}],
                "still_results": [{"shot_id": "S001", "image": "D:/renders/S001.png", "status": "done"}],
                "clip_results": [{"shot_id": "S001", "video": "D:/renders/S001.mp4", "status": "done"}],
            },
        )

        out = run_review_outputs(stage_input)

        assert out.payload["review_report"]["audio_video_drift_sec"] == 0.35
    finally:
        _Path.exists = _original_exists


def test_review_outputs_honors_explicit_quality_findings(monkeypatch):
    existing = {"D:/renders/final.mp4", "D:/renders/S006.png", "D:/renders/S006.mp4"}

    def _fake_exists(self):
        return str(self).replace("\\", "/") in {path.replace("\\", "/") for path in existing}

    from pathlib import Path as _Path

    _original_exists = _Path.exists
    _Path.exists = _fake_exists
    try:
        stage_input = StageInput(
            run_id="run-9",
            config={},
            payload={
                "final_video": "D:/renders/final.mp4",
                "shot_plan": [{"shot_id": "S006", "material_id": "MAT_006", "section_id": "SEC_006", "render_mode": "ia2v"}],
                "material_plan": [{"material_id": "MAT_006", "section_id": "SEC_006"}],
                "render_plan": [{"shot_id": "S006", "material_id": "MAT_006", "section_id": "SEC_006", "render_mode": "ia2v"}],
                "still_results": [{"shot_id": "S006", "image": "D:/renders/S006.png", "material_id": "MAT_006", "section_id": "SEC_006", "status": "done"}],
                "clip_results": [{"shot_id": "S006", "video": "D:/renders/S006.mp4", "material_id": "MAT_006", "section_id": "SEC_006", "status": "done"}],
                "review_inputs": {
                    "music_file": "D:/renders/song.mp3",
                    "quality_findings": {
                        "S006": ["terminal_frame_corruption", "continuity_break"],
                    },
                },
            },
        )

        out = run_review_outputs(stage_input)

        assert out.payload["review_report"]["status"] == "needs_rerender"
        assert out.payload["review_report"]["rerender_targets"] == ["S006"]
        assert out.payload["review_report"]["blocking_checks"]["terminal_frames_clean"] is False
        assert out.payload["review_report"]["blocking_checks"]["visual_continuity_preserved"] is False
        assert out.payload["review_report"]["benchmark_dimensions"]["temporal_coherence"]["passed"] is False
        assert out.payload["review_report"]["benchmark_dimensions"]["temporal_coherence"]["affected_shots"] == ["S006"]
        assert out.payload["review_report"]["benchmark_dimensions"]["continuity"]["reasons"] == ["continuity_break"]
        assert out.payload["review_report"]["review_signal_buckets"]["heuristic_proxy"]["passed"] is False
        assert out.payload["review_report"]["review_signal_buckets"]["heuristic_proxy"]["failed_checks"] == ["terminal_frames_clean", "visual_continuity_preserved"]
        assert out.payload["review_report"]["review_signal_buckets"]["model_judged"]["passed"] is False
        assert out.payload["review_report"]["publishability_summary"]["technical_completion"]["passed"] is True
        assert out.payload["review_report"]["publishability_summary"]["technical_completion"]["next_action"] == "no_action"
        assert out.payload["review_report"]["publishability_summary"]["technical_completion"]["rerender_bundle"] == {
            "action": "no_action",
            "target_shots": [],
            "reason_codes": [],
        }
        assert out.payload["review_report"]["publishability_summary"]["isolated_asset_quality"]["passed"] is False
        assert out.payload["review_report"]["publishability_summary"]["isolated_asset_quality"]["next_action"] == "rerender_clips_with_terminal_frame_cleanup"
        assert out.payload["review_report"]["publishability_summary"]["isolated_asset_quality"]["rerender_bundle"] == {
            "action": "rerender_clips_with_terminal_frame_cleanup",
            "target_shots": ["S006"],
            "target_material_ids": ["MAT_006"],
            "target_section_ids": ["SEC_006"],
            "reason_codes": ["terminal_frame_corruption"],
        }
        assert out.payload["review_report"]["publishability_summary"]["final_mv_publishability"]["passed"] is False
        assert out.payload["review_report"]["publishability_summary"]["final_mv_publishability"]["next_action"] == "rerender_continuity_break_shots"
        assert out.payload["review_report"]["publishability_summary"]["final_mv_publishability"]["rerender_bundle"] == {
            "action": "rerender_continuity_break_shots",
            "target_shots": ["S006"],
            "target_material_ids": ["MAT_006"],
            "target_section_ids": ["SEC_006"],
            "reason_codes": ["continuity_break"],
        }
        assert out.payload["review_report"]["rerender_plan"] == [
            {
                "shot_id": "S006",
                "reason_codes": ["terminal_frame_corruption", "continuity_break"],
                "priority_score": out.payload["review_report"]["rerender_priority_scores"]["S006"],
                "bucket": "isolated_asset_quality",
                "recommended_action": "rerender_clips_with_terminal_frame_cleanup",
                "execution_mode": "automatic",
                "rerender_prescription": {
                    "stage_focus": "clips",
                    "workflow_focus": ["ia2v"],
                    "prompt_contract_focus": ["clip_prompt_seed", "clip_positive_prompt"],
                    "fix_strategy": "shorter_motion_and_clean_terminal_frames",
                },
            }
        ]
        assert out.payload["review_report"]["rerender_payload"] == [
            {
                "shot_id": "S006",
                "quality_findings": ["terminal_frame_corruption", "continuity_break"],
                "rerender_stage": "clips",
                "workflow_focus": ["ia2v"],
                "prompt_contract_focus": ["clip_prompt_seed", "clip_positive_prompt"],
                "recommended_action": "rerender_clips_with_terminal_frame_cleanup",
                "fix_strategy": "shorter_motion_and_clean_terminal_frames",
            }
        ]
        assert out.payload["review_report"]["rerender_execution_payloads"] == [
            {
                "shot_id": "S006",
                "recommended_action": "rerender_clips_with_terminal_frame_cleanup",
                "rerender_stage": "clips",
                "execution_mode": "automatic",
                "workflow_focus": ["ia2v"],
                "prompt_contract_focus": ["clip_prompt_seed", "clip_positive_prompt"],
                "fix_strategy": "shorter_motion_and_clean_terminal_frames",
                "stage_payloads": {
                    "clips": {
                        "shot_plan": [{"shot_id": "S006", "material_id": "MAT_006", "section_id": "SEC_006", "render_mode": "ia2v"}],
                        "render_plan": [{"shot_id": "S006", "material_id": "MAT_006", "section_id": "SEC_006", "render_mode": "ia2v"}],
                        "still_results": [{"shot_id": "S006", "image": "D:/renders/S006.png", "material_id": "MAT_006", "section_id": "SEC_006", "status": "done"}],
                        "music_file": "",
                    }
                },
            }
        ]
    finally:
        _Path.exists = _original_exists



def test_review_outputs_loads_quality_findings_from_review_inputs_path(monkeypatch, tmp_path):
    findings_path = tmp_path / "review-findings.json"
    findings_path.write_text(
        '{\n'
        '  "review_inputs": {\n'
        '    "quality_findings": {\n'
        '      "S006": ["terminal_frame_corruption", "continuity_break"]\n'
        '    }\n'
        '  }\n'
        '}\n',
        encoding="utf-8",
    )
    existing = {"D:/renders/final.mp4", "D:/renders/S006.png", "D:/renders/S006.mp4", str(findings_path)}

    def _fake_exists(self):
        return str(self).replace("\\", "/") in {path.replace("\\", "/") for path in existing}

    from pathlib import Path as _Path

    _original_exists = _Path.exists
    _Path.exists = _fake_exists
    try:
        stage_input = StageInput(
            run_id="run-9b",
            config={},
            payload={
                "final_video": "D:/renders/final.mp4",
                "shot_plan": [{"shot_id": "S006"}],
                "still_results": [{"shot_id": "S006", "image": "D:/renders/S006.png", "status": "done"}],
                "clip_results": [{"shot_id": "S006", "video": "D:/renders/S006.mp4", "status": "done"}],
                "review_inputs": {
                    "music_file": "D:/renders/song.mp3",
                    "quality_findings_path": str(findings_path),
                },
            },
        )

        out = run_review_outputs(stage_input)

        assert out.payload["review_report"]["status"] == "needs_rerender"
        assert out.payload["review_report"]["rerender_targets"] == ["S006"]
        assert out.payload["review_report"]["blocking_checks"]["terminal_frames_clean"] is False
        assert out.payload["review_report"]["blocking_checks"]["visual_continuity_preserved"] is False
    finally:
        _Path.exists = _original_exists



def test_review_outputs_fails_when_configured_quality_findings_path_is_invalid(tmp_path):
    import pytest

    findings_path = tmp_path / "review-findings.json"
    findings_path.write_text('{"review_inputs": ', encoding="utf-8")
    stage_input = StageInput(
        run_id="run-9c",
        config={},
        payload={
            "final_video": "D:/renders/final.mp4",
            "shot_plan": [{"shot_id": "S006"}],
            "still_results": [{"shot_id": "S006", "image": "D:/renders/S006.png", "status": "done"}],
            "clip_results": [{"shot_id": "S006", "video": "D:/renders/S006.mp4", "status": "done"}],
            "review_inputs": {
                "music_file": "D:/renders/song.mp3",
                "quality_findings_path": str(findings_path),
            },
        },
    )

    with pytest.raises(RuntimeError, match="invalid review quality findings file"):
        run_review_outputs(stage_input)



def test_prepare_rerender_aggregates_review_execution_payloads_into_stage_inputs():
    stage_input = StageInput(
        run_id="run-rerender-1",
        config={},
        payload={
            "review_report": {
                "rerender_execution_payloads": [
                    {
                        "shot_id": "S003",
                        "recommended_action": "rerender_scene_intrusion_shots",
                        "rerender_stage": "stills",
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
                        "stage_payloads": {
                            "stills": {
                                "shot_plan": [{"shot_id": "S002", "material_id": "MAT_002", "render_mode": "ia2v"}],
                                "material_plan": [{"material_id": "MAT_002", "section_id": "SEC_002"}],
                                "render_plan": [{"shot_id": "S002", "material_id": "MAT_002", "render_mode": "ia2v", "clip_prompt_seed": "clip-2"}],
                                "style_bible": {"style": "synthwave"},
                            },
                            "clips": {
                                "shot_plan": [{"shot_id": "S002", "render_mode": "ia2v"}],
                                "render_plan": [{"shot_id": "S002", "material_id": "MAT_002", "render_mode": "ia2v", "clip_prompt_seed": "clip-2"}],
                                "still_results": [
                                    {"shot_id": "S002", "material_id": "MAT_002", "image": "still-2.png"},
                                    {"shot_id": "S004", "image": "still-4.png"},
                                ],
                                "music_file": "song.mp3",
                            },
                        },
                    },
                    {
                        "shot_id": "S006",
                        "recommended_action": "rerender_clips_with_terminal_frame_cleanup",
                        "rerender_stage": "clips",
                        "stage_payloads": {
                            "clips": {
                                "shot_plan": [{"shot_id": "S006", "render_mode": "ia2v"}],
                                "render_plan": [{"shot_id": "S006", "render_mode": "ia2v", "clip_prompt_seed": "clip-6"}],
                                "still_results": [{"shot_id": "S006", "image": "still-6.png"}],
                                "music_file": "",
                            }
                        },
                    },
                ]
            }
        },
    )

    out = run_prepare_rerender(stage_input)

    assert out.stage == "prepare_rerender"
    assert out.status == "done"
    assert out.payload == {
        "rerender_target_ids": ["S003", "S001", "S002", "S006"],
        "rerender_stage_sequence": ["stills", "clips"],
        "rerender_stage_inputs": {
                "stills": {
                    "shot_plan": [
                        {"shot_id": "S003", "material_id": "MAT_003", "render_mode": "ia2v"},
                        {"shot_id": "S001", "material_id": "MAT_001", "render_mode": "ia2v"},
                        {"shot_id": "S002", "material_id": "MAT_002", "render_mode": "ia2v"},
                    ],
                    "material_plan": [
                        {"material_id": "MAT_003", "section_id": "SEC_003"},
                        {"material_id": "MAT_001", "section_id": "SEC_001"},
                        {"material_id": "MAT_002", "section_id": "SEC_002"},
                    ],
                    "style_bible": {"style": "synthwave"},
                    "render_plan": [
                        {"shot_id": "S003", "material_id": "MAT_003", "render_mode": "ia2v", "still_prompt_text": "still-3"},
                        {"shot_id": "S001", "material_id": "MAT_001", "render_mode": "ia2v", "still_prompt_text": "still-1"},
                        {"shot_id": "S002", "material_id": "MAT_002", "render_mode": "ia2v", "clip_prompt_seed": "clip-2"},
                    ],
                    "still_results": [],
                },
            "clips": {
                "shot_plan": [
                    {"shot_id": "S002", "render_mode": "ia2v"},
                    {"shot_id": "S006", "render_mode": "ia2v"},
                ],
                "render_plan": [
                    {"shot_id": "S002", "material_id": "MAT_002", "render_mode": "ia2v", "clip_prompt_seed": "clip-2"},
                    {"shot_id": "S006", "render_mode": "ia2v", "clip_prompt_seed": "clip-6"},
                ],
                "still_results": [
                    {"shot_id": "S002", "material_id": "MAT_002", "image": "still-2.png"},
                    {"shot_id": "S004", "image": "still-4.png"},
                    {"shot_id": "S006", "image": "still-6.png"},
                ],
                "music_file": "song.mp3",
            },
        },
    }
    validate_stage_input("stills", out.payload["rerender_stage_inputs"]["stills"])



def test_prepare_rerender_returns_empty_stage_inputs_when_review_has_no_targets():
    stage_input = StageInput(
        run_id="run-rerender-empty",
        config={},
        payload={"review_report": {"rerender_execution_payloads": []}},
    )

    out = run_prepare_rerender(stage_input)

    assert out.payload == {
        "rerender_target_ids": [],
        "rerender_stage_sequence": [],
        "rerender_stage_inputs": {},
    }


def test_prepare_rerender_collects_review_stage_inputs_for_sync_repairs():
    out = run_prepare_rerender(
        StageInput(
            run_id="run-prepare-review-sync",
            config={},
            payload={
                "review_report": {
                    "status": "needs_rerender",
                    "rerender_targets": ["S001"],
                    "rerender_execution_payloads": [
                        {
                            "shot_id": "S001",
                            "recommended_action": "repair_audio_video_sync",
                            "rerender_stage": "review",
                            "stage_payloads": {
                                "review": {
                                    "final_video": "final-sync.mp4",
                                    "music_file": "song.mp3",
                                    "recommended_action": "repair_audio_video_sync",
                                    "target_shots": ["S001"],
                                    "target_material_ids": ["MAT_001"],
                                    "target_section_ids": ["SEC_001"],
                                }
                            },
                        }
                    ],
                }
            },
        )
    )

    assert out.payload == {
        "rerender_target_ids": ["S001"],
        "rerender_stage_sequence": ["review"],
        "rerender_stage_inputs": {
            "review": {
                "final_video": "final-sync.mp4",
                "music_file": "song.mp3",
                "recommended_action": "repair_audio_video_sync",
                "target_shots": ["S001"],
                "target_material_ids": ["MAT_001"],
                "target_section_ids": ["SEC_001"],
                "assembly_plan": {},
                "review_inputs": {},
            }
        },
    }



def test_prepare_rerender_backfills_review_stage_with_top_level_assembly_context():
    out = run_prepare_rerender(
        StageInput(
            run_id="run-prepare-review-assembly-context",
            config={},
            payload={
                "assembly_plan": {
                    "section_edit_map": {"SEC_001": {"section_id": "SEC_001", "selected_clip_ids": ["S001"]}},
                    "transition_map": {},
                    "timing_map": {},
                    "section_edits": [{"section_id": "SEC_001", "selected_clip_ids": ["S001"]}],
                },
                "review_inputs": {"cadence_profile_by_shot": {"S001": "support_hold"}},
                "review_report": {
                    "status": "needs_rerender",
                    "rerender_targets": ["S001"],
                    "rerender_execution_payloads": [
                        {
                            "shot_id": "S001",
                            "recommended_action": "revise_transition_selection",
                            "rerender_stage": "review",
                            "stage_payloads": {
                                "review": {
                                    "final_video": "final-sync.mp4",
                                    "music_file": "song.mp3",
                                    "recommended_action": "revise_transition_selection",
                                    "target_shots": ["S001"],
                                    "target_material_ids": ["MAT_001"],
                                    "target_section_ids": ["SEC_001"],
                                }
                            },
                        }
                    ],
                },
            },
        )
    )

    assert out.payload["rerender_stage_inputs"]["review"]["assembly_plan"] == {
        "section_edit_map": {"SEC_001": {"section_id": "SEC_001", "selected_clip_ids": ["S001"]}},
        "transition_map": {},
        "timing_map": {},
        "section_edits": [{"section_id": "SEC_001", "selected_clip_ids": ["S001"]}],
    }
    assert out.payload["rerender_stage_inputs"]["review"]["review_inputs"] == {
        "cadence_profile_by_shot": {"S001": "support_hold"}
    }



def test_prepare_rerender_merges_partial_review_stage_with_top_level_assembly_context():
    out = run_prepare_rerender(
        StageInput(
            run_id="run-prepare-review-assembly-merge",
            config={},
            payload={
                "assembly_plan": {
                    "section_edit_map": {
                        "SEC_001": {"section_id": "SEC_001", "selected_clip_ids": ["S001"]},
                        "SEC_002": {"section_id": "SEC_002", "selected_clip_ids": ["S002"]},
                    },
                    "transition_map": {"SEC_001": {"transition_in": "cut_in", "transition_out": "cut_out"}, "SEC_002": {"transition_in": "glide_in", "transition_out": "handoff_out"}},
                    "timing_map": {"SEC_001": {"snap_unit": "beat"}, "SEC_002": {"snap_unit": "bar"}},
                    "section_edits": [{"section_id": "SEC_001"}, {"section_id": "SEC_002"}],
                },
                "review_inputs": {
                    "edit_intent_by_shot": {
                        "S001": {"section_emphasis": "sequence_support"},
                        "S002": {"section_emphasis": "chorus_push"},
                    },
                    "cadence_profile_by_shot": {"S001": "support_hold", "S002": "hook_dense"},
                },
                "review_report": {
                    "status": "needs_rerender",
                    "rerender_targets": ["S001"],
                    "rerender_execution_payloads": [
                        {
                            "shot_id": "S001",
                            "recommended_action": "revise_transition_selection",
                            "rerender_stage": "review",
                            "stage_payloads": {
                                "review": {
                                    "final_video": "final-sync.mp4",
                                    "music_file": "song.mp3",
                                    "recommended_action": "revise_transition_selection",
                                    "target_shots": ["S001"],
                                    "target_material_ids": ["MAT_001"],
                                    "target_section_ids": ["SEC_001"],
                                    "assembly_plan": {
                                        "section_edit_map": {"SEC_001": {"section_id": "SEC_001", "selected_clip_ids": ["S001"]}},
                                        "transition_map": {"SEC_001": {"transition_in": "cut_in", "transition_out": "cut_out"}},
                                        "timing_map": {"SEC_001": {"snap_unit": "beat"}},
                                        "section_edits": [{"section_id": "SEC_001"}],
                                    },
                                    "review_inputs": {
                                        "edit_intent_by_shot": {"S001": {"section_emphasis": "sequence_support"}},
                                        "cadence_profile_by_shot": {"S001": "support_hold"},
                                    },
                                }
                            },
                        }
                    ],
                },
            },
        )
    )

    assert out.payload["rerender_stage_inputs"]["review"]["assembly_plan"] == {
        "section_edit_map": {
            "SEC_001": {"section_id": "SEC_001", "selected_clip_ids": ["S001"]},
            "SEC_002": {"section_id": "SEC_002", "selected_clip_ids": ["S002"]},
        },
        "transition_map": {"SEC_001": {"transition_in": "cut_in", "transition_out": "cut_out"}, "SEC_002": {"transition_in": "glide_in", "transition_out": "handoff_out"}},
        "timing_map": {"SEC_001": {"snap_unit": "beat"}, "SEC_002": {"snap_unit": "bar"}},
        "section_edits": [{"section_id": "SEC_001"}, {"section_id": "SEC_002"}],
    }
    assert out.payload["rerender_stage_inputs"]["review"]["review_inputs"] == {
        "edit_intent_by_shot": {
            "S001": {"section_emphasis": "sequence_support"},
            "S002": {"section_emphasis": "chorus_push"},
        },
        "cadence_profile_by_shot": {"S001": "support_hold", "S002": "hook_dense"},
    }



def test_prepare_rerender_prefers_canonical_top_level_review_context_over_stale_stage_subset():
    out = run_prepare_rerender(
        StageInput(
            run_id="run-prepare-review-assembly-override",
            config={},
            payload={
                "assembly_plan": {
                    "section_edit_map": {"SEC_001": {"section_id": "SEC_001", "selected_clip_ids": ["S001"], "editorial_weight": "high"}},
                    "transition_map": {"SEC_001": {"transition_in": "glide_in", "transition_out": "handoff_out"}},
                    "timing_map": {"SEC_001": {"snap_unit": "bar"}},
                    "section_edits": [{"section_id": "SEC_001", "editorial_weight": "high"}],
                },
                "review_inputs": {
                    "edit_intent_by_shot": {"S001": {"section_emphasis": "sequence_support", "transition_in": "glide_in", "transition_out": "handoff_out"}},
                    "cadence_profile_by_shot": {"S001": "support_release"},
                },
                "review_report": {
                    "rerender_execution_payloads": [
                        {
                            "shot_id": "S001",
                            "recommended_action": "revise_transition_selection",
                            "rerender_stage": "review",
                            "stage_payloads": {
                                "review": {
                                    "final_video": "final-sync.mp4",
                                    "music_file": "song.mp3",
                                    "recommended_action": "revise_transition_selection",
                                    "target_shots": ["S001"],
                                    "target_material_ids": ["MAT_001"],
                                    "target_section_ids": ["SEC_001"],
                                    "assembly_plan": {
                                        "section_edit_map": {"SEC_001": {"section_id": "SEC_001", "selected_clip_ids": ["S001"], "editorial_weight": "medium"}},
                                        "transition_map": {"SEC_001": {"transition_in": "cut_in", "transition_out": "cut_out"}},
                                        "timing_map": {"SEC_001": {"snap_unit": "beat"}},
                                        "section_edits": [{"section_id": "SEC_001", "editorial_weight": "medium"}],
                                    },
                                    "review_inputs": {
                                        "edit_intent_by_shot": {"S001": {"section_emphasis": "sequence_support", "transition_in": "cut_in", "transition_out": "cut_out"}},
                                        "cadence_profile_by_shot": {"S001": "support_hold"},
                                    },
                                }
                            },
                        }
                    ]
                },
            },
        )
    )

    assert out.payload["rerender_stage_inputs"]["review"]["assembly_plan"]["section_edit_map"]["SEC_001"]["editorial_weight"] == "high"
    assert out.payload["rerender_stage_inputs"]["review"]["assembly_plan"]["transition_map"]["SEC_001"] == {"transition_in": "glide_in", "transition_out": "handoff_out"}
    assert out.payload["rerender_stage_inputs"]["review"]["review_inputs"]["edit_intent_by_shot"]["S001"] == {"section_emphasis": "sequence_support", "transition_in": "glide_in", "transition_out": "handoff_out"}
    assert out.payload["rerender_stage_inputs"]["review"]["review_inputs"]["cadence_profile_by_shot"]["S001"] == "support_release"



def test_prepare_rerender_preserves_review_recommended_action_from_report_payloads():
    stage_input = StageInput(
        run_id="run-rerender-review-stage-assembly",
        config={},
        payload={
            "review_report": {
                "rerender_execution_payloads": [
                    {
                        "shot_id": "S001",
                        "recommended_action": "revise_assembly_weights_before_clip_rerender",
                        "rerender_stage": "review",
                        "stage_payloads": {
                            "review": {
                                "final_video": "final.mp4",
                                "music_file": "song.mp3",
                                "recommended_action": "revise_assembly_weights_before_clip_rerender",
                                "target_shots": ["S001"],
                                "target_material_ids": ["MAT_001"],
                                "target_section_ids": ["SEC_001"],
                            }
                        },
                    }
                ]
            }
        },
    )

    out = run_prepare_rerender(stage_input)

    assert out.payload["rerender_stage_inputs"]["review"]["recommended_action"] == "revise_assembly_weights_before_clip_rerender"
    assert out.payload["rerender_stage_inputs"]["review"]["target_shots"] == ["S001"]
    assert out.payload["rerender_stage_inputs"]["review"]["target_material_ids"] == ["MAT_001"]
    assert out.payload["rerender_stage_inputs"]["review"]["target_section_ids"] == ["SEC_001"]



def test_prepare_rerender_preserves_review_sync_repair_summary_for_coverage_revision():
    stage_input = StageInput(
        run_id="run-rerender-review-stage-sync-summary",
        config={},
        payload={
            "review_report": {
                "rerender_execution_payloads": [
                    {
                        "shot_id": "S001",
                        "recommended_action": "revise_assembly_coverage_before_sync_pad",
                        "rerender_stage": "review",
                        "stage_payloads": {
                            "review": {
                                "final_video": "final.mp4",
                                "music_file": "song.mp3",
                                "recommended_action": "revise_assembly_coverage_before_sync_pad",
                                "target_shots": ["S001"],
                                "target_material_ids": ["MAT_001"],
                                "target_section_ids": ["SEC_001"],
                                "sync_repair_summary": {
                                    "repair_strategy": "clone_tail_pad",
                                    "clone_tail_sec": 9.253,
                                    "clone_tail_ratio": 0.513,
                                    "clone_tail_excessive": True,
                                },
                            }
                        },
                    }
                ]
            }
        },
    )

    out = run_prepare_rerender(stage_input)

    assert out.payload["rerender_stage_inputs"]["review"]["sync_repair_summary"] == {
        "repair_strategy": "clone_tail_pad",
        "clone_tail_sec": 9.253,
        "clone_tail_ratio": 0.513,
        "clone_tail_excessive": True,
    }



def test_prepare_rerender_merges_review_target_provenance_across_multiple_payloads():
    stage_input = StageInput(
        run_id="run-rerender-review-stage-merge-targets",
        config={},
        payload={
            "review_report": {
                "rerender_execution_payloads": [
                    {
                        "shot_id": "S001",
                        "recommended_action": "revise_assembly_weights_before_clip_rerender",
                        "rerender_stage": "review",
                        "stage_payloads": {
                            "review": {
                                "final_video": "final.mp4",
                                "music_file": "song.mp3",
                                "recommended_action": "revise_assembly_weights_before_clip_rerender",
                                "target_shots": ["S001"],
                                "target_material_ids": ["MAT_001"],
                                "target_section_ids": ["SEC_001"],
                            }
                        },
                    },
                    {
                        "shot_id": "S002",
                        "recommended_action": "revise_assembly_weights_before_clip_rerender",
                        "rerender_stage": "review",
                        "stage_payloads": {
                            "review": {
                                "final_video": "final.mp4",
                                "music_file": "song.mp3",
                                "recommended_action": "revise_assembly_weights_before_clip_rerender",
                                "target_shots": ["S002"],
                                "target_material_ids": ["MAT_002"],
                                "target_section_ids": ["SEC_002"],
                            }
                        },
                    },
                ]
            }
        },
    )

    out = run_prepare_rerender(stage_input)

    assert out.payload["rerender_stage_inputs"]["review"] == {
        "final_video": "final.mp4",
        "music_file": "song.mp3",
        "recommended_action": "revise_assembly_weights_before_clip_rerender",
        "target_shots": ["S001", "S002"],
        "target_material_ids": ["MAT_001", "MAT_002"],
        "target_section_ids": ["SEC_001", "SEC_002"],
        "assembly_plan": {},
        "review_inputs": {},
    }



def test_execute_rerender_runs_review_stage_sync_repair(monkeypatch):


    calls = []

    def _fake_run_render_stills(stage_input):
        calls.append(("stills", stage_input.payload))
        return StageOutput("render_stills", "done", {"still_results": [{"shot_id": "S002", "image": "rerendered-2.png"}]}, [])

    def _fake_run_render_clips(stage_input):
        calls.append(("clips", stage_input.payload))
        return StageOutput("render_clips", "done", {"clip_results": [{"shot_id": "S002", "video": "rerendered-2.mp4"}]}, [])

    monkeypatch.setattr("ai_mv.core.stages.execute_rerender.run_render_stills", _fake_run_render_stills)
    monkeypatch.setattr("ai_mv.core.stages.execute_rerender.run_render_clips", _fake_run_render_clips)

    stage_input = StageInput(
        run_id="run-rerender-exec-1",
        config={"render": {"ltx_fps": 24}},
        payload={
            "rerender_stage_sequence": ["stills", "clips"],
            "rerender_stage_inputs": {
                "stills": {
                    "shot_plan": [{"shot_id": "S002", "material_id": "MAT_002", "render_mode": "ia2v"}],
                    "material_plan": [{"material_id": "MAT_002", "section_id": "SEC_002"}],
                    "render_plan": [{"shot_id": "S002", "material_id": "MAT_002", "render_mode": "ia2v", "still_prompt_text": "repair still"}],
                    "style_bible": {"style": "synthwave"},
                },
                "clips": {
                    "shot_plan": [{"shot_id": "S002", "render_mode": "ia2v"}],
                    "render_plan": [{"shot_id": "S002", "render_mode": "ia2v", "clip_prompt_seed": "repair clip"}],
                    "still_results": [
                        {"shot_id": "S002", "image": "stale-2.png"},
                        {"shot_id": "S004", "image": "bridge-4.png"},
                    ],
                    "music_file": "song.mp3",
                },
            },
        },
    )

    out = run_execute_rerender(stage_input)

    assert [name for name, _payload in calls] == ["stills", "clips"]
    assert calls[1][1]["still_results"] == [
        {"shot_id": "S004", "image": "bridge-4.png"},
        {"shot_id": "S002", "image": "rerendered-2.png"},
    ]
    assert out.stage == "execute_rerender"
    assert out.status == "done"
    assert out.payload == {
        "rerender_results": {
            "completed_stages": ["stills", "clips"],
            "still_results": [{"shot_id": "S002", "material_id": "MAT_002", "image": "rerendered-2.png"}],
            "clip_results": [{"shot_id": "S002", "video": "rerendered-2.mp4"}],
        }
    }



def test_execute_rerender_validates_stills_inputs_before_running(monkeypatch):
    called = []

    def _fake_run_render_stills(stage_input):
        called.append(stage_input.payload)
        return StageOutput("render_stills", "done", {"still_results": []}, [])

    monkeypatch.setattr("ai_mv.core.stages.execute_rerender.run_render_stills", _fake_run_render_stills)

    import pytest

    with pytest.raises(StageFailure):
        run_execute_rerender(
            StageInput(
                run_id="run-rerender-exec-invalid-stills",
                config={},
                payload={
                    "rerender_stage_sequence": ["stills"],
                    "rerender_stage_inputs": {
                        "stills": {
                            "shot_plan": [{"shot_id": "S002", "material_id": "MAT_002", "render_mode": "ia2v"}],
                            "material_plan": [{"material_id": "MAT_002", "section_id": "SEC_002"}],
                            "render_plan": [{"shot_id": "S002", "material_id": "MAT_999", "render_mode": "ia2v", "still_prompt_text": "repair still"}],
                            "style_bible": {"style": "synthwave"},
                        }
                    },
                },
            )
        )

    assert called == []



def test_repair_audio_video_sync_reports_excessive_clone_tail(monkeypatch, tmp_path):
    final_video = tmp_path / "mv.mp4"
    music_file = tmp_path / "song.mp3"
    final_video.write_text("video", encoding="utf-8")
    music_file.write_text("audio", encoding="utf-8")
    calls = []

    def _fake_repair_sync(final_video_path, music_file_path, output_video_path, *, video_duration, audio_duration):
        calls.append((final_video_path, music_file_path, output_video_path, video_duration, audio_duration))
        output_video_path.write_text("synced", encoding="utf-8")
        return True

    monkeypatch.setattr("ai_mv.core.stages.repair_audio_video_sync.resolve_generated_file", lambda _config, path, *_args: str(path))
    monkeypatch.setattr("ai_mv.core.stages.repair_audio_video_sync.ffprobe_duration", lambda path: 9.0 if Path(path).name == "mv.mp4" else 18.0)
    monkeypatch.setattr("ai_mv.core.stages.repair_audio_video_sync._repair_sync", _fake_repair_sync)

    out = run_repair_audio_video_sync(
        StageInput(
            run_id="run-sync-clone-tail",
            config={},
            payload={"final_video": str(final_video), "music_file": str(music_file)},
        )
    )

    assert out.payload["final_video"].endswith("mv_synced.mp4")
    assert out.payload["sync_repair_summary"] == {
        "input_video_duration_sec": 9.0,
        "audio_duration_sec": 18.0,
        "output_duration_sec": 18.0,
        "clone_tail_sec": 9.0,
        "clone_tail_ratio": 0.5,
        "clone_tail_excessive": True,
        "repair_strategy": "clone_tail_pad",
    }
    assert calls



def test_execute_rerender_runs_review_stage_sync_repair(monkeypatch):
    calls = []

    def _fake_repair_audio_video_sync(stage_input):
        calls.append(("review", stage_input.payload))
        return StageOutput(
            "repair_audio_video_sync",
            "done",
            {
                "final_video": "synced-final.mp4",
                "music_file": "song.mp3",
            },
            ["synced-final.mp4"],
        )

    monkeypatch.setattr("ai_mv.core.stages.execute_rerender.run_repair_audio_video_sync", _fake_repair_audio_video_sync)

    out = run_execute_rerender(
        StageInput(
            run_id="run-rerender-exec-review",
            config={},
            payload={
                "rerender_stage_sequence": ["review"],
                "rerender_stage_inputs": {
                    "review": {
                        "final_video": "final.mp4",
                        "music_file": "song.mp3",
                        "recommended_action": "repair_audio_video_sync",
                    }
                },
            },
        )
    )

    assert calls == [("review", {"final_video": "final.mp4", "music_file": "song.mp3"})]
    assert out.payload == {
        "rerender_results": {
            "completed_stages": ["review"],
            "still_results": [],
            "clip_results": [],
        },
        "final_video": "synced-final.mp4",
        "music_file": "song.mp3",
    }
    assert out.artifacts == ["synced-final.mp4"]



def test_execute_rerender_does_not_route_assembly_review_actions_into_sync_repair(monkeypatch):
    calls = []

    def _fake_repair_audio_video_sync(stage_input):
        calls.append(stage_input.payload)
        return StageOutput("repair_audio_video_sync", "done", {"final_video": "should-not-run.mp4"}, [])

    monkeypatch.setattr("ai_mv.core.stages.execute_rerender.run_repair_audio_video_sync", _fake_repair_audio_video_sync)

    out = run_execute_rerender(
        StageInput(
            run_id="run-rerender-exec-assembly-review",
            config={},
            payload={
                "rerender_stage_sequence": ["review"],
                "rerender_stage_inputs": {
                    "review": {
                        "final_video": "final.mp4",
                        "music_file": "song.mp3",
                        "recommended_action": "revise_assembly_weights_before_clip_rerender",
                        "target_shots": ["S010", "S011"],
                        "target_material_ids": ["MAT_010", "MAT_011"],
                        "target_section_ids": ["SEC_010", "SEC_011"],
                    }
                },
            },
        )
    )

    assert calls == []
    assert out.payload == {
        "rerender_results": {
            "completed_stages": ["review"],
            "still_results": [],
            "clip_results": [],
        },
        "final_video": "final.mp4",
        "music_file": "song.mp3",
        "review_action": "revise_assembly_weights_before_clip_rerender",
        "review_inputs": {
            "assembly_revision": {
                "action": "revise_assembly_weights_before_clip_rerender",
                "target": "assembly",
                "final_video": "final.mp4",
                "music_file": "song.mp3",
                "target_shots": ["S010", "S011"],
                "target_material_ids": ["MAT_010", "MAT_011"],
                "target_section_ids": ["SEC_010", "SEC_011"],
                "revised_review_inputs": {
                    "cadence_profile_by_shot": {},
                    "snap_unit_by_shot": {},
                    "trimmed_coverage_by_shot": {},
                    "edit_intent_by_shot": {},
                },
            }
        },
        "assembly_revision_result": {
            "action": "revise_assembly_weights_before_clip_rerender",
            "status": "applied",
            "target": "assembly",
            "output_final_video": "final.mp4",
            "revision_focus": "weights",
            "target_shots": ["S010", "S011"],
            "target_material_ids": ["MAT_010", "MAT_011"],
            "target_section_ids": ["SEC_010", "SEC_011"],
            "revised_assembly_plan": {
                "section_edit_map": {},
                "transition_map": {},
                "timing_map": {},
                "section_edits": [],
            },
        },
    }
    assert out.artifacts == []



def test_execute_rerender_emits_distinct_transition_revision_payload(monkeypatch):
    calls = []
    assembly_calls = []

    def _fake_repair_audio_video_sync(stage_input):
        calls.append(stage_input.payload)
        return StageOutput("repair_audio_video_sync", "done", {"final_video": "should-not-run.mp4"}, [])

    def _fake_render_revised_assembly(*, config, run_id, music_file, final_video, review_inputs, revised_assembly_plan, revisions_by_shot):
        assembly_calls.append(
            {
                "run_id": run_id,
                "music_file": music_file,
                "final_video": final_video,
                "review_inputs": review_inputs,
                "revised_assembly_plan": revised_assembly_plan,
                "revisions_by_shot": revisions_by_shot,
            }
        )
        return {
            "final_video": "final-revised.mp4",
            "artifacts": ["final-revised.mp4"],
        }

    monkeypatch.setattr("ai_mv.core.stages.execute_rerender.run_repair_audio_video_sync", _fake_repair_audio_video_sync)
    monkeypatch.setattr("ai_mv.core.stages.execute_rerender._render_revised_assembly", _fake_render_revised_assembly)

    out = run_execute_rerender(
        StageInput(
            run_id="run-rerender-exec-transition-review",
            config={},
            payload={
                "rerender_stage_sequence": ["review"],
                "rerender_stage_inputs": {
                    "review": {
                        "final_video": "final.mp4",
                        "music_file": "song.mp3",
                        "recommended_action": "revise_transition_selection",
                        "assembly_plan": {
                            "section_edit_map": {
                                "SEC_001": {
                                    "section_id": "SEC_001",
                                    "selected_clip_ids": ["S001"],
                                    "selected_material_ids": ["MAT_001"],
                                    "transition_in": "cut_in",
                                    "transition_out": "cut_out",
                                    "snap_unit": "free",
                                    "cadence_profile": "support_hold",
                                    "trimmed_coverage_sec": 4.0,
                                }
                            },
                            "transition_map": {"SEC_001": {"transition_in": "cut_in", "transition_out": "cut_out"}},
                            "timing_map": {"SEC_001": {"selected_clip_ids": ["S001"], "snap_unit": "free", "cadence_profile": "support_hold", "trimmed_coverage_sec": 4.0}},
                            "section_edits": [{"section_id": "SEC_001", "selected_clip_ids": ["S001"], "transition_in": "cut_in", "transition_out": "cut_out", "snap_unit": "free", "cadence_profile": "support_hold", "trimmed_coverage_sec": 4.0}],
                        },
                        "review_inputs": {
                            "clip_results": [{"shot_id": "S001", "video": "clip1.mp4", "section_id": "SEC_001", "material_id": "MAT_001"}],
                            "edit_intent_by_shot": {"S001": {"section_emphasis": "sequence_support"}},
                            "cadence_profile_by_shot": {"S001": "support_hold"},
                            "snap_unit_by_shot": {"S001": "free"},
                            "trimmed_coverage_by_shot": {"S001": 4.0},
                        },
                        "target_shots": ["S001"],
                        "target_material_ids": ["MAT_001"],
                        "target_section_ids": ["SEC_001"],
                    }
                },
            },
        )
    )

    assert calls == []
    assert assembly_calls[0]["run_id"] == "run-rerender-exec-transition-review"
    assert assembly_calls[0]["final_video"] == "final.mp4"
    assert out.payload["final_video"] == "final-revised.mp4"
    assert out.payload["review_action"] == "revise_transition_selection"
    assert out.payload["review_inputs"]["assembly_revision"]["revised_review_inputs"] == {
        "cadence_profile_by_shot": {"S001": "support_release"},
        "snap_unit_by_shot": {"S001": "beat"},
        "trimmed_coverage_by_shot": {"S001": 3.6},
        "edit_intent_by_shot": {
            "S001": {
                "section_emphasis": "sequence_support",
                "transition_in": "glide_in",
                "transition_out": "handoff_out",
            }
        },
    }
    assert out.payload["review_inputs"]["edit_intent_by_shot"]["S001"] == {
        "section_emphasis": "sequence_support",
        "transition_in": "glide_in",
        "transition_out": "handoff_out",
    }
    assert out.payload["assembly_revision_result"]["status"] == "applied"
    assert out.payload["assembly_revision_result"]["output_final_video"] == "final-revised.mp4"
    assert out.payload["assembly_revision_result"]["revised_assembly_plan"]["transition_map"]["SEC_001"] == {
        "transition_in": "glide_in",
        "transition_out": "handoff_out",
    }
    assert out.artifacts == ["final-revised.mp4"]



def test_execute_rerender_applies_weight_revision_to_assembly_metadata(monkeypatch):
    monkeypatch.setattr("ai_mv.core.stages.execute_rerender.run_repair_audio_video_sync", lambda stage_input: StageOutput("repair_audio_video_sync", "done", {}, []))

    out = run_execute_rerender(
        StageInput(
            run_id="run-rerender-exec-weight-review",
            config={},
            payload={
                "rerender_stage_sequence": ["review"],
                "rerender_stage_inputs": {
                    "review": {
                        "final_video": "final.mp4",
                        "music_file": "song.mp3",
                        "recommended_action": "revise_assembly_weights_before_clip_rerender",
                        "assembly_plan": {
                            "section_edit_map": {
                                "SEC_001": {
                                    "section_id": "SEC_001",
                                    "selected_clip_ids": ["S010", "S011"],
                                    "selected_material_ids": ["MAT_010", "MAT_011"],
                                    "editorial_weight": "medium",
                                    "snap_unit": "beat",
                                    "cadence_profile": "support_hold",
                                    "trimmed_coverage_sec": 4.0,
                                }
                            },
                            "transition_map": {"SEC_001": {"transition_in": "cut_in", "transition_out": "cut_out"}},
                            "timing_map": {"SEC_001": {"selected_clip_ids": ["S010", "S011"], "snap_unit": "beat", "cadence_profile": "support_hold", "trimmed_coverage_sec": 4.0}},
                            "section_edits": [{"section_id": "SEC_001", "selected_clip_ids": ["S010", "S011"], "editorial_weight": "medium", "snap_unit": "beat", "cadence_profile": "support_hold", "trimmed_coverage_sec": 4.0}],
                        },
                        "review_inputs": {
                            "edit_intent_by_shot": {
                                "S010": {"section_emphasis": "chorus_push"},
                                "S011": {"section_emphasis": "chorus_push"},
                            },
                            "cadence_profile_by_shot": {"S010": "support_hold", "S011": "support_hold"},
                            "snap_unit_by_shot": {"S010": "beat", "S011": "beat"},
                            "trimmed_coverage_by_shot": {"S010": 4.0, "S011": 4.0},
                        },
                        "target_shots": ["S010", "S011"],
                        "target_material_ids": ["MAT_010", "MAT_011"],
                        "target_section_ids": ["SEC_001"],
                    }
                },
            },
        )
    )

    revised_inputs = out.payload["review_inputs"]["assembly_revision"]["revised_review_inputs"]
    assert revised_inputs == {
        "cadence_profile_by_shot": {"S010": "hook_dense", "S011": "hook_dense"},
        "snap_unit_by_shot": {"S010": "bar", "S011": "bar"},
        "trimmed_coverage_by_shot": {"S010": 3.2, "S011": 3.2},
        "edit_intent_by_shot": {
            "S010": {"section_emphasis": "chorus_push", "transition_in": "cut_in", "transition_out": "cut_out"},
            "S011": {"section_emphasis": "chorus_push", "transition_in": "cut_in", "transition_out": "cut_out"},
        },
    }
    assert out.payload["assembly_revision_result"]["revised_assembly_plan"]["section_edit_map"]["SEC_001"]["editorial_weight"] == "high"
    assert out.payload["assembly_revision_result"]["revised_assembly_plan"]["timing_map"]["SEC_001"]["trimmed_coverage_sec"] == 3.2



def test_execute_rerender_uses_clone_tail_summary_to_extend_assembly_coverage(monkeypatch):
    assembly_calls = []

    def _fake_render_revised_assembly(*, config, run_id, music_file, final_video, review_inputs, revised_assembly_plan, revisions_by_shot):
        assembly_calls.append(
            {
                "review_inputs": review_inputs,
                "revised_assembly_plan": revised_assembly_plan,
                "revisions_by_shot": revisions_by_shot,
            }
        )
        return {"final_video": "final-coverage-revised.mp4", "artifacts": ["final-coverage-revised.mp4"]}

    monkeypatch.setattr("ai_mv.core.stages.execute_rerender._render_revised_assembly", _fake_render_revised_assembly)

    out = run_execute_rerender(
        StageInput(
            run_id="run-rerender-exec-coverage-review",
            config={},
            payload={
                "rerender_stage_sequence": ["review"],
                "rerender_stage_inputs": {
                    "review": {
                        "final_video": "final.mp4",
                        "music_file": "song.mp3",
                        "recommended_action": "revise_assembly_coverage_before_sync_pad",
                        "sync_repair_summary": {"clone_tail_sec": 8.0, "clone_tail_excessive": True},
                        "assembly_plan": {
                            "section_edit_map": {
                                "SEC_001": {
                                    "section_id": "SEC_001",
                                    "selected_clip_ids": ["S001"],
                                    "selected_material_ids": ["MAT_001"],
                                    "transition_in": "cut_in",
                                    "transition_out": "cut_out",
                                    "snap_unit": "free",
                                    "cadence_profile": "support_hold",
                                    "trimmed_coverage_sec": 4.0,
                                }
                            },
                            "transition_map": {"SEC_001": {"transition_in": "cut_in", "transition_out": "cut_out"}},
                            "timing_map": {"SEC_001": {"selected_clip_ids": ["S001"], "snap_unit": "free", "cadence_profile": "support_hold", "trimmed_coverage_sec": 4.0}},
                            "section_edits": [{"section_id": "SEC_001", "selected_clip_ids": ["S001"], "transition_in": "cut_in", "transition_out": "cut_out", "snap_unit": "free", "cadence_profile": "support_hold", "trimmed_coverage_sec": 4.0}],
                        },
                        "review_inputs": {
                            "clip_results": [{"shot_id": "S001", "video": "clip1.mp4", "section_id": "SEC_001", "material_id": "MAT_001"}],
                            "edit_intent_by_shot": {"S001": {"section_emphasis": "sequence_support"}},
                            "trimmed_coverage_by_shot": {"S001": 4.0},
                        },
                        "target_shots": ["S001"],
                        "target_material_ids": ["MAT_001"],
                        "target_section_ids": ["SEC_001"],
                    }
                },
            },
        )
    )

    assert out.payload["review_action"] == "revise_assembly_coverage_before_sync_pad"
    assert out.payload["final_video"] == "final-coverage-revised.mp4"
    revised_inputs = out.payload["review_inputs"]["assembly_revision"]["revised_review_inputs"]
    assert revised_inputs["trimmed_coverage_by_shot"] == {"S001": 12.0}
    assert assembly_calls[0]["revisions_by_shot"]["S001"]["trimmed_coverage_sec"] == 12.0
    assert out.payload["assembly_revision_result"]["revised_assembly_plan"]["timing_map"]["SEC_001"]["trimmed_coverage_sec"] == 12.0



def test_apply_assembly_coverage_revision_distributes_clone_tail_extension_across_targeted_sections():
    from ai_mv.core.stages.assemble_mv import apply_assembly_revision

    revised_plan, revisions_by_shot = apply_assembly_revision(
        {
            "section_edit_map": {
                "SEC_001": {"section_id": "SEC_001", "selected_clip_ids": ["S001"], "trimmed_coverage_sec": 4.0},
                "SEC_002": {"section_id": "SEC_002", "selected_clip_ids": ["S002"], "trimmed_coverage_sec": 2.0},
            },
            "timing_map": {
                "SEC_001": {"trimmed_coverage_sec": 4.0},
                "SEC_002": {"trimmed_coverage_sec": 2.0},
            },
            "transition_map": {"SEC_001": {}, "SEC_002": {}},
            "section_edits": [
                {"section_id": "SEC_001", "selected_clip_ids": ["S001"], "trimmed_coverage_sec": 4.0},
                {"section_id": "SEC_002", "selected_clip_ids": ["S002"], "trimmed_coverage_sec": 2.0},
            ],
        },
        action="revise_assembly_coverage_before_sync_pad",
        target_shots=["S001", "S002"],
        coverage_extension_sec=6.0,
    )

    assert revised_plan["timing_map"]["SEC_001"]["trimmed_coverage_sec"] == 7.0
    assert revised_plan["timing_map"]["SEC_002"]["trimmed_coverage_sec"] == 5.0
    assert revisions_by_shot["S001"]["trimmed_coverage_sec"] == 7.0
    assert revisions_by_shot["S002"]["trimmed_coverage_sec"] == 5.0



def test_render_revised_assembly_repeats_clip_segments_when_coverage_revision_exceeds_media_duration(monkeypatch, tmp_path):
    from ai_mv.core.stages import execute_rerender as execute_rerender_module

    mux_calls = []

    def _fake_resolve(_config, path, *_args):
        return str(tmp_path / Path(path).name)

    def _fake_duration(path):
        return {"clip-a.mp4": 4.0, "clip-b.mp4": 3.0, "song.mp3": 18.0}.get(Path(path).name, 0.0)

    def _fake_mux(clips, audio, out, config):
        mux_calls.append({"clips": clips, "audio": audio, "out": out, "config": config})
        return True

    monkeypatch.setattr("ai_mv.core.stages.execute_rerender.resolve_generated_file", _fake_resolve)
    monkeypatch.setattr("ai_mv.core.stages.execute_rerender.ffprobe_duration", _fake_duration)
    monkeypatch.setattr("ai_mv.core.stages.execute_rerender.run_ffmpeg_mux", _fake_mux)
    for name in ("clip-a.mp4", "clip-b.mp4", "song.mp3"):
        (tmp_path / name).write_text(name, encoding="utf-8")

    result = execute_rerender_module._render_revised_assembly(
        config={"video": {"target": "640x360@24"}},
        run_id="run-coverage-render-repeat",
        music_file="song.mp3",
        final_video=str(tmp_path / "final.mp4"),
        review_inputs={
            "clip_results": [
                {"shot_id": "S001", "video": "clip-a.mp4"},
                {"shot_id": "S002", "video": "clip-b.mp4"},
            ]
        },
        revised_assembly_plan={
            "section_edits": [
                {"section_id": "SEC_001", "selected_clip_ids": ["S001"]},
                {"section_id": "SEC_002", "selected_clip_ids": ["S002"]},
            ]
        },
        revisions_by_shot={
            "S001": {"trimmed_coverage_sec": 6.0},
            "S002": {"trimmed_coverage_sec": 1.5},
        },
    )

    assert result["final_video"] == str(tmp_path / "final.mp4")
    segments = mux_calls[0]["clips"]
    assert [(segment["shot_id"], segment["trim_start_sec"], segment["trim_end_sec"]) for segment in segments] == [
        ("S001", 0.0, 4.0),
        ("S001", 0.0, 2.0),
        ("S002", 0.0, 1.5),
    ]



def test_rerender_review_preserves_real_assembly_revision_result():
    out = run_rerender_review(
        StageInput(
            run_id="run-rerender-review-assembly-result",
            config={},
            payload={
                "final_video": "D:/renders/final.mp4",
                "music_file": "D:/renders/song.mp3",
                "shot_plan": [{"shot_id": "S001"}],
                "render_plan": [{"shot_id": "S001", "render_mode": "ia2v"}],
                "still_results": [{"shot_id": "S001", "image": "D:/renders/S001.png", "status": "done"}],
                "clip_results": [{"shot_id": "S001", "video": "D:/renders/S001.mp4", "status": "done"}],
                "review_inputs": {
                    "music_file": "D:/renders/song.mp3",
                    "assembly_revision": {
                        "action": "revise_transition_selection",
                        "target": "assembly",
                        "final_video": "D:/renders/final.mp4",
                        "music_file": "D:/renders/song.mp3",
                    },
                },
                "review_action": "revise_transition_selection",
                "assembly_revision_result": {
                    "action": "revise_transition_selection",
                    "status": "ready",
                    "target": "assembly",
                    "output_final_video": "D:/renders/final.mp4",
                    "revision_focus": "transitions",
                },
                "rerender_results": {
                    "completed_stages": ["review"],
                    "still_results": [],
                    "clip_results": [],
                },
            },
        )
    )

    assert out.payload["assembly_revision_result"] == {
        "action": "revise_transition_selection",
        "status": "ready",
        "target": "assembly",
        "output_final_video": "D:/renders/final.mp4",
        "revision_focus": "transitions",
        "improvement_summary": {
            "targeted_issue_improved": False,
            "before_repetitive_edit_risk_score": 0.0,
            "after_repetitive_edit_risk_score": 0.0,
            "before_safe_editing_within_threshold": False,
            "after_safe_editing_within_threshold": False,
            "before_transition_intentionality_score": 0.0,
            "after_transition_intentionality_score": 0.0,
            "before_slideshow_risk_within_threshold": False,
            "after_slideshow_risk_within_threshold": False,
        },
    }
    assert out.payload["assembly_plan"] == {}



def test_execute_rerender_returns_empty_results_when_no_rerender_stage_inputs_exist():
    out = run_execute_rerender(
        StageInput(
            run_id="run-rerender-exec-empty",
            config={},
            payload={"rerender_stage_sequence": [], "rerender_stage_inputs": {}},
        )
    )

    assert out.payload == {
        "rerender_results": {
            "completed_stages": [],
            "still_results": [],
            "clip_results": [],
        }
    }


def test_rerender_review_merges_fresh_assets_and_recomputes_review(monkeypatch):

    existing = {"D:/renders/final.mp4", "D:/renders/S001_retry.png", "D:/renders/S001_retry.mp4"}

    def _fake_exists(self):
        return str(self).replace("\\", "/") in {path.replace("\\", "/") for path in existing}

    from pathlib import Path as _Path

    _original_exists = _Path.exists
    _Path.exists = _fake_exists
    try:
        stage_input = StageInput(
            run_id="run-rerender-review-1",
            config={},
            payload={
                "final_video": "D:/renders/final.mp4",
                "music_file": "D:/renders/song.mp3",
                "shot_plan": [{"shot_id": "S001"}],
                "render_plan": [{"shot_id": "S001", "render_mode": "ia2v"}],
                "still_results": [{"shot_id": "S001", "image": "", "status": "failed"}],
                "clip_results": [{"shot_id": "S001", "video": "", "status": "failed"}],
                "review_inputs": {"music_file": "D:/renders/song.mp3", "quality_findings": {"S001": []}},
                "rerender_results": {
                    "completed_stages": ["stills", "clips"],
                    "still_results": [{"shot_id": "S001", "image": "D:/renders/S001_retry.png", "status": "done"}],
                    "clip_results": [{"shot_id": "S001", "video": "D:/renders/S001_retry.mp4", "status": "done"}],
                },
            },
        )

        out = run_rerender_review(stage_input)

        assert out.stage == "rerender_review"
        assert out.status == "done"
        assert out.payload["still_results"] == [{"shot_id": "S001", "image": "D:/renders/S001_retry.png", "status": "done"}]
        assert out.payload["clip_results"] == [{"shot_id": "S001", "video": "D:/renders/S001_retry.mp4", "status": "done"}]
        assert out.payload["rerender_review_report"]["status"] == "done"
        assert out.payload["rerender_review_report"]["rerender_targets"] == []
    finally:
        _Path.exists = _original_exists



def test_rerender_review_drops_stale_manual_findings_for_rerendered_shots(monkeypatch, tmp_path):

    findings_path = tmp_path / "review-findings.json"
    findings_path.write_text(
        '{"review_inputs": {"quality_findings": {"S001": ["weak_character_payoff", "background_dominant_composition"], "S009": ["continuity_break"]}}}\n',
        encoding="utf-8",
    )
    existing = {
        "D:/renders/final.mp4",
        "D:/renders/song.mp3",
        "D:/renders/S001_retry.png",
        "D:/renders/S001_retry.mp4",
        "D:/renders/S009.png",
        "D:/renders/S009.mp4",
        str(findings_path),
    }

    def _fake_exists(self):
        return str(self).replace("\\", "/") in {path.replace("\\", "/") for path in existing}

    from pathlib import Path as _Path

    _original_exists = _Path.exists
    _Path.exists = _fake_exists
    try:
        out = run_rerender_review(
            StageInput(
                run_id="run-rerender-review-drop-stale-findings",
                config={},
                payload={
                    "final_video": "D:/renders/final.mp4",
                    "music_file": "D:/renders/song.mp3",
                    "shot_plan": [{"shot_id": "S001"}, {"shot_id": "S009"}],
                    "render_plan": [{"shot_id": "S001", "render_mode": "ia2v"}, {"shot_id": "S009", "render_mode": "ia2v"}],
                    "still_results": [{"shot_id": "S001", "image": "", "status": "failed"}, {"shot_id": "S009", "image": "D:/renders/S009.png", "status": "done"}],
                    "clip_results": [{"shot_id": "S001", "video": "", "status": "failed"}, {"shot_id": "S009", "video": "D:/renders/S009.mp4", "status": "done"}],
                    "review_inputs": {
                        "music_file": "D:/renders/song.mp3",
                        "quality_findings": {"S001": ["weak_character_payoff", "background_dominant_composition"]},
                        "quality_findings_path": str(findings_path),
                    },
                    "rerender_results": {
                        "completed_stages": ["stills", "clips"],
                        "still_results": [{"shot_id": "S001", "image": "D:/renders/S001_retry.png", "status": "done"}],
                        "clip_results": [{"shot_id": "S001", "video": "D:/renders/S001_retry.mp4", "status": "done"}],
                    },
                },
            )
        )

        assert out.payload["rerender_review_report"]["status"] == "needs_rerender"
        assert out.payload["rerender_review_report"]["rerender_targets"] == ["S009"]
        assert out.payload["review_inputs"] == {
            "music_file": "D:/renders/song.mp3",
            "quality_findings": {"S009": ["continuity_break"]},
        }
    finally:
        _Path.exists = _original_exists



def test_rerender_review_preserves_manual_findings_for_failed_rerender_attempts(monkeypatch, tmp_path):

    findings_path = tmp_path / "review-findings.json"
    findings_path.write_text(
        '{"review_inputs": {"quality_findings": {"S001": ["weak_character_payoff"], "S009": ["continuity_break"]}}}\n',
        encoding="utf-8",
    )
    existing = {
        "D:/renders/final.mp4",
        "D:/renders/song.mp3",
        "D:/renders/S009.png",
        "D:/renders/S009.mp4",
        str(findings_path),
    }

    def _fake_exists(self):
        return str(self).replace("\\", "/") in {path.replace("\\", "/") for path in existing}

    from pathlib import Path as _Path

    _original_exists = _Path.exists
    _Path.exists = _fake_exists
    try:
        out = run_rerender_review(
            StageInput(
                run_id="run-rerender-review-preserve-failed-findings",
                config={},
                payload={
                    "final_video": "D:/renders/final.mp4",
                    "music_file": "D:/renders/song.mp3",
                    "shot_plan": [{"shot_id": "S001"}, {"shot_id": "S009"}],
                    "render_plan": [{"shot_id": "S001", "render_mode": "ia2v"}, {"shot_id": "S009", "render_mode": "ia2v"}],
                    "still_results": [{"shot_id": "S001", "image": "", "status": "failed"}, {"shot_id": "S009", "image": "D:/renders/S009.png", "status": "done"}],
                    "clip_results": [{"shot_id": "S001", "video": "", "status": "failed"}, {"shot_id": "S009", "video": "D:/renders/S009.mp4", "status": "done"}],
                    "review_inputs": {
                        "music_file": "D:/renders/song.mp3",
                        "quality_findings_path": str(findings_path),
                    },
                    "rerender_results": {
                        "completed_stages": ["stills", "clips"],
                        "still_results": [{"shot_id": "S001", "image": "", "status": "failed"}],
                        "clip_results": [{"shot_id": "S001", "video": "", "status": "failed"}],
                    },
                },
            )
        )

        assert out.payload["rerender_review_report"]["rerender_targets"] == ["S001", "S009"]
        assert out.payload["review_inputs"] == {
            "music_file": "D:/renders/song.mp3",
            "quality_findings": {
                "S001": ["weak_character_payoff"],
                "S009": ["continuity_break"],
            },
        }
    finally:
        _Path.exists = _original_exists



def test_rerender_review_raises_for_invalid_quality_findings_path(tmp_path):
    import pytest

    findings_path = tmp_path / "review-findings.json"
    findings_path.write_text('{"review_inputs": ', encoding="utf-8")

    with pytest.raises(RuntimeError, match="invalid review quality findings file"):
        run_rerender_review(
            StageInput(
                run_id="run-rerender-review-invalid-findings",
                config={},
                payload={
                    "final_video": "D:/renders/final.mp4",
                    "music_file": "D:/renders/song.mp3",
                    "shot_plan": [{"shot_id": "S001"}],
                    "render_plan": [{"shot_id": "S001", "render_mode": "ia2v"}],
                    "still_results": [{"shot_id": "S001", "image": "D:/renders/S001.png", "status": "done"}],
                    "clip_results": [{"shot_id": "S001", "video": "D:/renders/S001.mp4", "status": "done"}],
                    "review_inputs": {
                        "music_file": "D:/renders/song.mp3",
                        "quality_findings_path": str(findings_path),
                    },
                    "rerender_results": {
                        "completed_stages": [],
                        "still_results": [],
                        "clip_results": [],
                    },
                },
            )
        )



def test_rerender_review_preserves_assembly_revision_review_inputs():
    out = run_rerender_review(
        StageInput(
            run_id="run-rerender-review-assembly-action",
            config={},
            payload={
                "final_video": "D:/renders/final.mp4",
                "music_file": "D:/renders/song.mp3",
                "shot_plan": [{"shot_id": "S001"}],
                "render_plan": [{"shot_id": "S001", "render_mode": "ia2v"}],
                "still_results": [{"shot_id": "S001", "image": "D:/renders/S001.png", "status": "done"}],
                "clip_results": [{"shot_id": "S001", "video": "D:/renders/S001.mp4", "status": "done"}],
                "review_inputs": {
                    "music_file": "D:/renders/song.mp3",
                    "assembly_revision": {
                        "action": "revise_assembly_weights_before_clip_rerender",
                        "target": "assembly",
                        "final_video": "D:/renders/final.mp4",
                        "music_file": "D:/renders/song.mp3",
                        "target_shots": ["S010", "S011"],
                        "target_material_ids": ["MAT_010", "MAT_011"],
                        "target_section_ids": ["SEC_010", "SEC_011"],
                    },
                },
                "review_action": "revise_assembly_weights_before_clip_rerender",
                "rerender_results": {
                    "completed_stages": ["review"],
                    "still_results": [],
                    "clip_results": [],
                },
            },
        )
    )

    assert out.payload["review_inputs"] == {
        "music_file": "D:/renders/song.mp3",
        "assembly_revision": {
            "action": "revise_assembly_weights_before_clip_rerender",
            "target": "assembly",
            "final_video": "D:/renders/final.mp4",
            "music_file": "D:/renders/song.mp3",
            "target_shots": ["S010", "S011"],
            "target_material_ids": ["MAT_010", "MAT_011"],
            "target_section_ids": ["SEC_010", "SEC_011"],
        },
    }
    assert out.payload["review_action"] == "revise_assembly_weights_before_clip_rerender"
    assert out.payload["rerender_final_video"] == "D:/renders/final.mp4"
    assert out.payload["rerender_review_report"]["assembly_revision_summary"] == {
        "present": True,
        "action": "revise_assembly_weights_before_clip_rerender",
        "target": "assembly",
        "final_video": "D:/renders/final.mp4",
        "music_file": "D:/renders/song.mp3",
        "target_shots": ["S010", "S011"],
        "target_material_ids": ["MAT_010", "MAT_011"],
        "target_section_ids": ["SEC_010", "SEC_011"],
    }



def test_rerender_review_reports_assembly_revision_improvement_from_revised_metadata():
    out = run_rerender_review(
        StageInput(
            run_id="run-rerender-review-assembly-improvement",
            config={},
            payload={
                "final_video": "D:/renders/final.mp4",
                "music_file": "D:/renders/song.mp3",
                "shot_plan": [
                    {"shot_id": "S010", "section": "chorus", "section_role": "hook", "section_emphasis": "chorus_push"},
                    {"shot_id": "S011", "section": "chorus", "section_role": "hook", "section_emphasis": "chorus_push"},
                    {"shot_id": "S012", "section": "verse", "section_role": "support", "section_emphasis": "sequence_support"},
                ],
                "render_plan": [
                    {"shot_id": "S010", "render_mode": "ia2v", "section_role": "hook"},
                    {"shot_id": "S011", "render_mode": "ia2v", "section_role": "hook"},
                    {"shot_id": "S012", "render_mode": "ia2v", "section_role": "support"},
                ],
                "clip_results": [
                    {"shot_id": "S010", "video": "D:/renders/S010.mp4", "status": "done"},
                    {"shot_id": "S011", "video": "D:/renders/S011.mp4", "status": "done"},
                    {"shot_id": "S012", "video": "D:/renders/S012.mp4", "status": "done"},
                ],
                "review_report": {
                    "assembly_quality_summary": {
                        "repetitive_edit_risk_score": 0.92,
                        "safe_editing_within_threshold": False,
                    }
                },
                "review_inputs": {
                    "music_file": "D:/renders/song.mp3",
                    "edit_intent_by_shot": {
                        "S010": {"section_emphasis": "chorus_push"},
                        "S011": {"section_emphasis": "chorus_push"},
                        "S012": {"section_emphasis": "sequence_support"},
                    },
                    "cadence_profile_by_shot": {"S010": "support_hold", "S011": "support_hold", "S012": "support_hold"},
                    "snap_unit_by_shot": {"S010": "beat", "S011": "beat", "S012": "beat"},
                    "trimmed_coverage_by_shot": {"S010": 4.0, "S011": 4.0, "S012": 4.0},
                    "assembly_revision": {
                        "action": "revise_assembly_weights_before_clip_rerender",
                        "target": "assembly",
                        "final_video": "D:/renders/final.mp4",
                        "music_file": "D:/renders/song.mp3",
                        "target_shots": ["S010", "S011"],
                        "target_material_ids": ["MAT_010", "MAT_011"],
                        "target_section_ids": ["SEC_001"],
                    },
                },
                "assembly_plan": {
                    "section_edit_map": {
                        "SEC_001": {
                            "section_id": "SEC_001",
                            "selected_clip_ids": ["S010", "S011"],
                            "selected_material_ids": ["MAT_010", "MAT_011"],
                            "editorial_weight": "medium",
                            "snap_unit": "beat",
                            "cadence_profile": "support_hold",
                            "trimmed_coverage_sec": 4.0,
                        },
                        "SEC_002": {
                            "section_id": "SEC_002",
                            "selected_clip_ids": ["S012"],
                            "selected_material_ids": ["MAT_012"],
                            "editorial_weight": "medium",
                            "snap_unit": "beat",
                            "cadence_profile": "support_hold",
                            "trimmed_coverage_sec": 4.0,
                        },
                    },
                    "transition_map": {"SEC_001": {"transition_in": "cut_in", "transition_out": "cut_out"}, "SEC_002": {"transition_in": "cut_in", "transition_out": "cut_out"}},
                    "timing_map": {"SEC_001": {"selected_clip_ids": ["S010", "S011"], "snap_unit": "beat", "cadence_profile": "support_hold", "trimmed_coverage_sec": 4.0}, "SEC_002": {"selected_clip_ids": ["S012"], "snap_unit": "beat", "cadence_profile": "support_hold", "trimmed_coverage_sec": 4.0}},
                    "section_edits": [
                        {"section_id": "SEC_001", "selected_clip_ids": ["S010", "S011"], "editorial_weight": "medium", "snap_unit": "beat", "cadence_profile": "support_hold", "trimmed_coverage_sec": 4.0},
                        {"section_id": "SEC_002", "selected_clip_ids": ["S012"], "editorial_weight": "medium", "snap_unit": "beat", "cadence_profile": "support_hold", "trimmed_coverage_sec": 4.0},
                    ],
                },
                "review_action": "revise_assembly_weights_before_clip_rerender",
                "assembly_revision_result": {
                    "action": "revise_assembly_weights_before_clip_rerender",
                    "status": "applied",
                    "target": "assembly",
                    "output_final_video": "D:/renders/final.mp4",
                    "revision_focus": "weights",
                    "revised_assembly_plan": {
                        "section_edit_map": {
                            "SEC_001": {
                                "section_id": "SEC_001",
                                "selected_clip_ids": ["S010", "S011"],
                                "selected_material_ids": ["MAT_010", "MAT_011"],
                                "editorial_weight": "high",
                                "snap_unit": "bar",
                                "cadence_profile": "hook_dense",
                                "trimmed_coverage_sec": 3.2,
                            },
                            "SEC_002": {
                                "section_id": "SEC_002",
                                "selected_clip_ids": ["S012"],
                                "selected_material_ids": ["MAT_012"],
                                "editorial_weight": "medium",
                                "snap_unit": "beat",
                                "cadence_profile": "support_hold",
                                "trimmed_coverage_sec": 4.0,
                            },
                        },
                        "transition_map": {"SEC_001": {"transition_in": "cut_in", "transition_out": "cut_out"}, "SEC_002": {"transition_in": "cut_in", "transition_out": "cut_out"}},
                        "timing_map": {"SEC_001": {"selected_clip_ids": ["S010", "S011"], "snap_unit": "bar", "cadence_profile": "hook_dense", "trimmed_coverage_sec": 3.2}, "SEC_002": {"selected_clip_ids": ["S012"], "snap_unit": "beat", "cadence_profile": "support_hold", "trimmed_coverage_sec": 4.0}},
                        "section_edits": [
                            {"section_id": "SEC_001", "selected_clip_ids": ["S010", "S011"], "editorial_weight": "high", "snap_unit": "bar", "cadence_profile": "hook_dense", "trimmed_coverage_sec": 3.2},
                            {"section_id": "SEC_002", "selected_clip_ids": ["S012"], "editorial_weight": "medium", "snap_unit": "beat", "cadence_profile": "support_hold", "trimmed_coverage_sec": 4.0},
                        ],
                    },
                },
                "rerender_results": {
                    "completed_stages": ["review"],
                    "still_results": [],
                    "clip_results": [],
                    "review_inputs": {
                        "cadence_profile_by_shot": {"S010": "hook_dense", "S011": "hook_dense", "S012": "support_hold"},
                        "snap_unit_by_shot": {"S010": "bar", "S011": "bar", "S012": "beat"},
                        "trimmed_coverage_by_shot": {"S010": 3.2, "S011": 3.2, "S012": 4.0},
                    },
                },
            },
        )
    )

    improvement = out.payload["assembly_revision_result"]["improvement_summary"]
    assert improvement["targeted_issue_improved"] is True
    assert improvement["before_repetitive_edit_risk_score"] == 0.92
    assert improvement["after_repetitive_edit_risk_score"] < improvement["before_repetitive_edit_risk_score"]
    assert out.payload["assembly_plan"] == out.payload["assembly_revision_result"]["revised_assembly_plan"]
    assert out.payload["review_inputs"]["cadence_profile_by_shot"] == {
        "S010": "hook_dense",
        "S011": "hook_dense",
        "S012": "support_hold",
    }



def test_rerender_review_reports_transition_revision_improvement_from_revised_transitions():
    out = run_rerender_review(
        StageInput(
            run_id="run-rerender-review-transition-improvement",
            config={},
            payload={
                "final_video": "D:/renders/final.mp4",
                "music_file": "D:/renders/song.mp3",
                "shot_plan": [
                    {"shot_id": "S001", "section": "verse", "section_role": "support", "section_emphasis": "sequence_support", "transition_in": "cut_in", "transition_out": "cut_out"},
                    {"shot_id": "S002", "section": "chorus", "section_role": "hook", "section_emphasis": "chorus_push", "transition_in": "cut_in", "transition_out": "cut_out"},
                    {"shot_id": "S003", "section": "bridge", "section_role": "support", "section_emphasis": "bridge_lift", "transition_in": "cut_in", "transition_out": "cut_out"},
                ],
                "render_plan": [
                    {"shot_id": "S001", "render_mode": "ia2v", "section_role": "support"},
                    {"shot_id": "S002", "render_mode": "ia2v", "section_role": "hook"},
                    {"shot_id": "S003", "render_mode": "ia2v", "section_role": "support"},
                ],
                "clip_results": [
                    {"shot_id": "S001", "video": "D:/renders/S001.mp4", "status": "done"},
                    {"shot_id": "S002", "video": "D:/renders/S002.mp4", "status": "done"},
                    {"shot_id": "S003", "video": "D:/renders/S003.mp4", "status": "done"},
                ],
                "review_report": {
                    "assembly_quality_summary": {
                        "transition_intentionality_score": 0.0,
                        "slideshow_risk_within_threshold": False,
                    }
                },
                "review_inputs": {
                    "edit_intent_by_shot": {
                        "S001": {"section_emphasis": "sequence_support", "transition_in": "cut_in", "transition_out": "cut_out"},
                        "S002": {"section_emphasis": "chorus_push", "transition_in": "cut_in", "transition_out": "cut_out"},
                        "S003": {"section_emphasis": "bridge_lift", "transition_in": "cut_in", "transition_out": "cut_out"},
                    },
                    "cadence_profile_by_shot": {"S001": "support_hold", "S002": "hook_dense", "S003": "bridge_pivot"},
                    "snap_unit_by_shot": {"S001": "beat", "S002": "bar", "S003": "beat"},
                    "trimmed_coverage_by_shot": {"S001": 4.0, "S002": 3.2, "S003": 3.8},
                    "assembly_revision": {
                        "action": "revise_transition_selection",
                        "target": "assembly",
                        "final_video": "D:/renders/final.mp4",
                        "music_file": "D:/renders/song.mp3",
                        "target_shots": ["S001"],
                        "target_material_ids": ["MAT_001"],
                        "target_section_ids": ["SEC_001"],
                    },
                },
                "assembly_revision_result": {
                    "action": "revise_transition_selection",
                    "status": "applied",
                    "target": "assembly",
                    "output_final_video": "D:/renders/final.mp4",
                    "revision_focus": "transitions",
                    "revised_assembly_plan": {
                        "section_edit_map": {
                            "SEC_001": {"section_id": "SEC_001", "selected_clip_ids": ["S001"], "selected_material_ids": ["MAT_001"], "transition_in": "glide_in", "transition_out": "handoff_out", "snap_unit": "beat", "cadence_profile": "support_release", "trimmed_coverage_sec": 3.6}
                        },
                        "transition_map": {"SEC_001": {"transition_in": "glide_in", "transition_out": "handoff_out"}},
                        "timing_map": {"SEC_001": {"selected_clip_ids": ["S001"], "snap_unit": "beat", "cadence_profile": "support_release", "trimmed_coverage_sec": 3.6}},
                        "section_edits": [{"section_id": "SEC_001", "selected_clip_ids": ["S001"], "transition_in": "glide_in", "transition_out": "handoff_out", "snap_unit": "beat", "cadence_profile": "support_release", "trimmed_coverage_sec": 3.6}],
                    },
                },
                "rerender_results": {
                    "completed_stages": ["review"],
                    "still_results": [],
                    "clip_results": [],
                    "review_inputs": {
                        "edit_intent_by_shot": {
                            "S001": {"section_emphasis": "sequence_support", "transition_in": "glide_in", "transition_out": "handoff_out"}
                        },
                        "cadence_profile_by_shot": {"S001": "support_release"},
                        "snap_unit_by_shot": {"S001": "beat"},
                        "trimmed_coverage_by_shot": {"S001": 3.6},
                    },
                },
            },
        )
    )

    improvement = out.payload["assembly_revision_result"]["improvement_summary"]
    assert improvement["targeted_issue_improved"] is True
    assert improvement["after_transition_intentionality_score"] > improvement["before_transition_intentionality_score"]
    assert out.payload["assembly_plan"] == out.payload["assembly_revision_result"]["revised_assembly_plan"]
    assert out.payload["review_inputs"]["edit_intent_by_shot"]["S001"]["transition_in"] == "glide_in"
    assert out.payload["review_inputs"]["edit_intent_by_shot"]["S001"]["transition_out"] == "handoff_out"



def test_rerender_review_scores_transition_improvement_on_targeted_subset_not_global_average():
    shot_plan = [{"shot_id": "S001", "section_emphasis": "sequence_support", "transition_in": "cut_in", "transition_out": "cut_out"}]
    shot_plan.extend({"shot_id": f"S{idx:03d}", "section_emphasis": "sequence_support", "transition_in": "cut_in", "transition_out": "cut_out"} for idx in range(2, 41))
    render_plan = [{"shot_id": row["shot_id"], "render_mode": "ia2v", "section_role": "support"} for row in shot_plan]
    clip_results = [{"shot_id": row["shot_id"], "video": f"D:/renders/{row['shot_id']}.mp4", "status": "done"} for row in shot_plan]
    edit_intent_before = {row["shot_id"]: {"section_emphasis": "sequence_support", "transition_in": "cut_in", "transition_out": "cut_out"} for row in shot_plan}
    edit_intent_after = dict(edit_intent_before)
    edit_intent_after["S001"] = {"section_emphasis": "sequence_support", "transition_in": "glide_in", "transition_out": "handoff_out"}

    out = run_rerender_review(
        StageInput(
            run_id="run-rerender-review-transition-targeted-subset",
            config={},
            payload={
                "final_video": "D:/renders/final.mp4",
                "music_file": "D:/renders/song.mp3",
                "shot_plan": shot_plan,
                "render_plan": render_plan,
                "clip_results": clip_results,
                "review_report": {
                    "assembly_quality_summary": {
                        "transition_intentionality_score": 0.0,
                        "slideshow_risk_within_threshold": False,
                    }
                },
                "review_inputs": {
                    "edit_intent_by_shot": edit_intent_before,
                    "cadence_profile_by_shot": {row["shot_id"]: "support_hold" for row in shot_plan},
                    "snap_unit_by_shot": {row["shot_id"]: "beat" for row in shot_plan},
                    "trimmed_coverage_by_shot": {row["shot_id"]: 4.0 for row in shot_plan},
                    "assembly_revision": {
                        "action": "revise_transition_selection",
                        "target": "assembly",
                        "final_video": "D:/renders/final.mp4",
                        "music_file": "D:/renders/song.mp3",
                        "target_shots": ["S001"],
                        "target_material_ids": ["MAT_001"],
                        "target_section_ids": ["SEC_001"],
                    },
                },
                "assembly_revision_result": {
                    "action": "revise_transition_selection",
                    "status": "applied",
                    "target": "assembly",
                    "output_final_video": "D:/renders/final.mp4",
                    "revision_focus": "transitions",
                    "target_shots": ["S001"],
                    "target_material_ids": ["MAT_001"],
                    "target_section_ids": ["SEC_001"],
                    "revised_assembly_plan": {"section_edit_map": {"SEC_001": {"section_id": "SEC_001"}}, "transition_map": {"SEC_001": {"transition_in": "glide_in", "transition_out": "handoff_out"}}, "timing_map": {"SEC_001": {"snap_unit": "beat"}}, "section_edits": [{"section_id": "SEC_001"}]},
                },
                "rerender_results": {
                    "completed_stages": ["review"],
                    "still_results": [],
                    "clip_results": [],
                    "review_inputs": {
                        "edit_intent_by_shot": {"S001": edit_intent_after["S001"]},
                        "cadence_profile_by_shot": {"S001": "support_release"},
                        "snap_unit_by_shot": {"S001": "beat"},
                        "trimmed_coverage_by_shot": {"S001": 3.6},
                    },
                },
            },
        )
    )

    improvement = out.payload["assembly_revision_result"]["improvement_summary"]
    assert improvement["targeted_issue_improved"] is True
    assert improvement["before_transition_intentionality_score"] == 0.0
    assert improvement["after_transition_intentionality_score"] == 1.0



def test_rerender_review_keeps_existing_assets_for_unmodified_shots():
    out = run_rerender_review(
        StageInput(
            run_id="run-rerender-review-2",
            config={},
            payload={
                "shot_plan": [{"shot_id": "S001"}, {"shot_id": "S002"}],
                "still_results": [
                    {"shot_id": "S001", "image": "still-1.png", "status": "done"},
                    {"shot_id": "S002", "image": "still-2.png", "status": "done"},
                ],
                "clip_results": [
                    {"shot_id": "S001", "video": "clip-1.mp4", "status": "done"},
                    {"shot_id": "S002", "video": "clip-2.mp4", "status": "done"},
                ],
                "rerender_results": {
                    "completed_stages": ["stills"],
                    "still_results": [{"shot_id": "S001", "image": "still-1-retry.png", "status": "done"}],
                    "clip_results": [],
                },
            },
        )
    )

    assert out.payload["still_results"] == [
        {"shot_id": "S002", "image": "still-2.png", "status": "done"},
        {"shot_id": "S001", "image": "still-1-retry.png", "status": "done"},
    ]
    assert out.payload["clip_results"] == [
        {"shot_id": "S001", "video": "clip-1.mp4", "status": "done"},
        {"shot_id": "S002", "video": "clip-2.mp4", "status": "done"},
    ]



def test_repair_rerender_prompts_applies_fix_strategies_to_stage_inputs():
    stage_input = StageInput(
        run_id="run-rerender-repair-1",
        config={},
        payload={
            "review_report": {
                "rerender_execution_payloads": [
                    {
                        "shot_id": "S001",
                        "recommended_action": "rerender_panelized_keyframes",
                        "rerender_stage": "stills",
                        "fix_strategy": "enforce_single_frame_keyframe_composition",
                        "prompt_contract_focus": ["still_prompt_text"],
                        "stage_payloads": {},
                    },
                    {
                        "shot_id": "S002",
                        "recommended_action": "rerender_scene_intrusion_shots",
                        "rerender_stage": "stills_then_clips",
                        "fix_strategy": "tighten_subject_and_world_anchors",
                        "prompt_contract_focus": ["still_prompt_text"],
                        "stage_payloads": {},
                    },
                    {
                        "shot_id": "S004",
                        "recommended_action": "rerender_weak_shots_with_prompt_tightening",
                        "rerender_stage": "stills",
                        "fix_strategy": "tighten_subject_identity_anchors",
                        "prompt_contract_focus": ["still_prompt_text"],
                        "stage_payloads": {},
                    },
                    {
                        "shot_id": "S005",
                        "recommended_action": "rerender_weak_shots_with_prompt_tightening",
                        "rerender_stage": "stills_then_clips",
                        "fix_strategy": "tighten_identity_continuity_anchors",
                        "prompt_contract_focus": ["still_prompt_text", "clip_prompt_seed", "clip_positive_prompt"],
                        "stage_payloads": {},
                    },
                    {
                        "shot_id": "S003",
                        "recommended_action": "rerender_clips_with_terminal_frame_cleanup",
                        "rerender_stage": "clips",
                        "fix_strategy": "shorter_motion_and_clean_terminal_frames",
                        "prompt_contract_focus": ["clip_prompt_seed", "clip_positive_prompt"],
                        "stage_payloads": {},
                    },
                    {
                        "shot_id": "S006",
                        "recommended_action": "rerender_character_payoff_shots",
                        "rerender_stage": "stills_then_clips",
                        "fix_strategy": "strengthen_character_payoff_and_subject_scale",
                        "prompt_contract_focus": ["still_prompt_text", "clip_prompt_seed", "clip_positive_prompt"],
                        "stage_payloads": {},
                    },
                ]
            },
            "rerender_stage_inputs": {
                "stills": {
                    "shot_plan": [{"shot_id": "S001"}, {"shot_id": "S002"}, {"shot_id": "S004"}, {"shot_id": "S005"}, {"shot_id": "S006"}],
                    "render_plan": [
                        {"shot_id": "S001", "still_prompt_text": "neon portrait"},
                        {"shot_id": "S002", "still_prompt_text": "night street singer"},
                        {"shot_id": "S004", "still_prompt_text": "rooftop heroine close-up", "reference_mode": "anchor_source", "edit_variation_scope": "none"},
                        {"shot_id": "S005", "still_prompt_text": "subway reflection heroine", "reference_mode": "use_performance_anchor_still", "edit_variation_scope": "performance_pose_upgrade"},
                        {"shot_id": "S006", "still_prompt_text": "wide neon bridge at dusk"},
                    ],
                },
                "clips": {
                    "shot_plan": [{"shot_id": "S003"}, {"shot_id": "S005"}, {"shot_id": "S006"}],
                    "render_plan": [
                        {
                            "shot_id": "S003",
                            "clip_prompt_seed": "camera drift forward, stable motion, preserve subject continuity",
                            "clip_positive_prompt": "camera drift forward, stable motion, preserve subject continuity, single continuous motion, no abrupt pose change",
                        },
                        {
                            "shot_id": "S005",
                            "clip_prompt_seed": "subway sidestep motion, keep protagonist recognizable",
                            "clip_positive_prompt": "subway sidestep motion, keep protagonist recognizable, stable body silhouette, no abrupt pose change",
                        },
                        {
                            "shot_id": "S006",
                            "clip_prompt_seed": "slow bridge walk, dreamy city lights",
                            "clip_positive_prompt": "slow bridge walk, dreamy city lights, cinematic atmosphere",
                        }
                    ],
                    "still_results": [],
                    "music_file": "song.mp3",
                },
            },
        },
    )

    out = run_repair_rerender_prompts(stage_input)

    still_rows = out.payload["rerender_stage_inputs"]["stills"]["render_plan"]
    clip_rows = out.payload["rerender_stage_inputs"]["clips"]["render_plan"]
    assert still_rows[0]["still_prompt_text"] == "neon portrait, single cinematic keyframe, one uninterrupted composition, no panel layout, no collage, no split screen"
    assert still_rows[1]["still_prompt_text"] == "night street singer, same protagonist, same environment, locked world details, no unrelated scene intrusion"
    assert still_rows[2]["still_prompt_text"] == "rooftop heroine close-up, same protagonist, locked identity details, no identity drift, no duplicate subject"
    assert "match adjacent shots" not in still_rows[2]["still_prompt_text"]
    assert "preserve neighboring-shot continuity" not in still_rows[2]["still_prompt_text"]
    assert "preserve face shape from the anchor still" not in still_rows[2]["still_prompt_text"]
    assert still_rows[3]["still_prompt_text"] == "subway reflection heroine, same protagonist, continuity-locked identity details, match adjacent shots, no identity drift, preserve neighboring-shot continuity, preserve face shape from the anchor still, avoid near-duplicate framing"
    assert still_rows[4]["still_prompt_text"] == "wide neon bridge at dusk, same protagonist, stronger character payoff, subject-led composition, larger foreground subject, no background-dominant framing"
    assert clip_rows[0]["clip_prompt_seed"] == "camera drift forward, clean terminal frame, restrained motion range"
    assert clip_rows[0]["clip_positive_prompt"] == "camera drift forward, clean terminal frame, restrained motion range, shorter motion beat, clean exit frame, no abrupt pose change"
    assert clip_rows[1]["clip_prompt_seed"] == "subway sidestep motion, same protagonist, preserve neighboring-shot continuity"
    assert clip_rows[1]["clip_positive_prompt"] == "subway sidestep motion, same protagonist, preserve neighboring-shot continuity, match adjacent shots, no identity drift, no abrupt pose change"
    assert clip_rows[2]["clip_prompt_seed"] == "slow bridge walk, same protagonist, stronger character payoff, larger foreground subject"
    assert clip_rows[2]["clip_positive_prompt"] == "slow bridge walk, dreamy city lights, cinematic atmosphere, same protagonist, stronger character payoff, subject-led composition, larger foreground subject, no background-dominant framing"



def test_repair_rerender_prompts_strengthens_story_payoff_and_chorus_release_contracts():
    stage_input = StageInput(
        run_id="run-rerender-story-repair",
        config={},
        payload={
            "review_report": {
                "rerender_execution_payloads": [
                    {
                        "shot_id": "S005",
                        "recommended_action": "rerender_character_payoff_shots",
                        "rerender_stage": "stills_then_clips",
                        "fix_strategy": "strengthen_story_payoff_and_chorus_release",
                        "prompt_contract_focus": ["still_prompt_text", "clip_prompt_seed", "clip_positive_prompt"],
                        "stage_payloads": {},
                    }
                ]
            },
            "rerender_stage_inputs": {
                "stills": {
                    "render_plan": [
                        {
                            "shot_id": "S005",
                            "still_prompt_text": "neon chorus wide shot",
                            "story_function": "release",
                            "payoff_requirement": "the hook must read as a visible emotional turn",
                        }
                    ]
                },
                "clips": {
                    "render_plan": [
                        {
                            "shot_id": "S005",
                            "clip_prompt_seed": "chorus walk under signs",
                            "clip_positive_prompt": "chorus walk under signs, steady camera",
                            "story_function": "release",
                            "payoff_requirement": "the hook must read as a visible emotional turn",
                        }
                    ]
                },
            },
        },
    )

    out = run_repair_rerender_prompts(stage_input)

    still_prompt = out.payload["rerender_stage_inputs"]["stills"]["render_plan"][0]["still_prompt_text"]
    clip_seed = out.payload["rerender_stage_inputs"]["clips"]["render_plan"][0]["clip_prompt_seed"]
    clip_positive = out.payload["rerender_stage_inputs"]["clips"]["render_plan"][0]["clip_positive_prompt"]
    assert "visible emotional turn" in still_prompt
    assert "chorus release lift" in still_prompt
    assert "not another safe mood-only shot" in still_prompt
    assert "visible emotional turn" in clip_seed
    assert "chorus release lift" in clip_positive
    assert "clear story beat fulfillment" in clip_positive


def test_repair_rerender_prompts_leaves_inputs_unchanged_when_no_execution_payloads_exist():
    stage_input = StageInput(
        run_id="run-rerender-repair-empty",
        config={},
        payload={
            "review_report": {"rerender_execution_payloads": []},
            "rerender_stage_inputs": {
                "stills": {
                    "shot_plan": [{"shot_id": "S001"}],
                    "render_plan": [{"shot_id": "S001", "still_prompt_text": "keep me"}],
                }
            },
        },
    )

    out = run_repair_rerender_prompts(stage_input)

    assert out.payload["rerender_stage_inputs"] == stage_input.payload["rerender_stage_inputs"]



def test_rerender_loop_chains_prepare_repair_execute_and_review(monkeypatch):
    calls = []

    def _fake_prepare(stage_input):
        calls.append(("prepare", dict(stage_input.payload)))
        return StageOutput(
            "prepare_rerender",
            "done",
            {
                "rerender_stage_sequence": ["stills"],
                "rerender_stage_inputs": {
                    "stills": {
                        "shot_plan": [{"shot_id": "S001"}],
                        "render_plan": [{"shot_id": "S001", "still_prompt_text": "draft"}],
                    }
                },
            },
            [],
        )

    def _fake_repair(stage_input):
        calls.append(("repair", dict(stage_input.payload)))
        assert stage_input.payload["rerender_stage_inputs"]["stills"]["render_plan"][0]["still_prompt_text"] == "draft"
        return StageOutput(
            "repair_rerender_prompts",
            "done",
            {
                "rerender_stage_inputs": {
                    "stills": {
                        "shot_plan": [{"shot_id": "S001"}],
                        "render_plan": [{"shot_id": "S001", "still_prompt_text": "repaired"}],
                    }
                }
            },
            [],
        )

    def _fake_execute(stage_input):
        calls.append(("execute", dict(stage_input.payload)))
        assert stage_input.payload["rerender_stage_inputs"]["stills"]["render_plan"][0]["still_prompt_text"] == "repaired"
        return StageOutput(
            "execute_rerender",
            "done",
            {
                "rerender_results": {
                    "completed_stages": ["stills"],
                    "still_results": [{"shot_id": "S001", "image": "retry.png", "status": "done"}],
                    "clip_results": [],
                }
            },
            [],
        )

    def _fake_review(stage_input):
        calls.append(("review", dict(stage_input.payload)))
        assert stage_input.payload["rerender_results"]["still_results"] == [{"shot_id": "S001", "image": "retry.png", "status": "done"}]
        return StageOutput(
            "rerender_review",
            "done",
            {
                "still_results": [{"shot_id": "S001", "image": "retry.png", "status": "done"}],
                "clip_results": [],
                "rerender_review_report": {"status": "done", "rerender_targets": []},
            },
            [],
        )

    monkeypatch.setattr("ai_mv.core.stages.rerender_loop.run_prepare_rerender", _fake_prepare)
    monkeypatch.setattr("ai_mv.core.stages.rerender_loop.run_repair_rerender_prompts", _fake_repair)
    monkeypatch.setattr("ai_mv.core.stages.rerender_loop.run_execute_rerender", _fake_execute)
    monkeypatch.setattr("ai_mv.core.stages.rerender_loop.run_rerender_review", _fake_review)

    out = run_rerender_loop(
        StageInput(
            run_id="run-rerender-loop-1",
            config={},
            payload={"review_report": {"rerender_execution_payloads": [{"shot_id": "S001"}]}, "still_results": []},
        )
    )

    assert [name for name, _payload in calls] == ["prepare", "repair", "execute", "review"]
    assert out.stage == "rerender_loop"
    assert out.status == "done"
    assert out.payload["rerender_stage_inputs"]["stills"]["render_plan"][0]["still_prompt_text"] == "repaired"
    assert out.payload["rerender_results"]["still_results"] == [{"shot_id": "S001", "image": "retry.png", "status": "done"}]
    assert out.payload["rerender_review_report"] == {"status": "done", "rerender_targets": []}
    assert out.payload["rerender_outcome"] == {"attempted": True, "resolved": True, "exhausted": False}


def test_rerender_loop_preserves_execute_stage_artifacts(monkeypatch):
    monkeypatch.setattr(
        "ai_mv.core.stages.rerender_loop.run_prepare_rerender",
        lambda stage_input: StageOutput("prepare_rerender", "done", {"rerender_stage_sequence": ["review"], "rerender_stage_inputs": {"review": {"final_video": "final.mp4", "music_file": "song.mp3"}}}, []),
    )
    monkeypatch.setattr(
        "ai_mv.core.stages.rerender_loop.run_repair_rerender_prompts",
        lambda stage_input: StageOutput("repair_rerender_prompts", "done", {"rerender_stage_inputs": {"review": {"final_video": "final.mp4", "music_file": "song.mp3"}}}, []),
    )
    monkeypatch.setattr(
        "ai_mv.core.stages.rerender_loop.run_execute_rerender",
        lambda stage_input: StageOutput(
            "execute_rerender",
            "done",
            {
                "rerender_results": {"completed_stages": ["review"], "still_results": [], "clip_results": []},
                "final_video": "synced-final.mp4",
                "assembly_revision_result": {"action": "revise_transition_selection", "revised_assembly_plan": {"section_edit_map": {"SEC_001": {"section_id": "SEC_001"}}, "transition_map": {}, "timing_map": {}, "section_edits": []}},
            },
            ["synced-final.mp4"],
        ),
    )
    monkeypatch.setattr(
        "ai_mv.core.stages.rerender_loop.run_rerender_review",
        lambda stage_input: StageOutput(
            "rerender_review",
            "done",
            {"rerender_review_report": {"status": "done", "rerender_targets": []}, "still_results": [], "clip_results": [], "assembly_plan": {"section_edit_map": {"SEC_001": {"section_id": "SEC_001"}}, "transition_map": {}, "timing_map": {}, "section_edits": []}},
            [],
        ),
    )

    out = run_rerender_loop(StageInput(run_id="run-rerender-loop-artifacts", config={}, payload={"review_report": {"status": "needs_rerender"}}))

    assert out.payload["rerender_final_video"] == "synced-final.mp4"
    assert out.payload["assembly_plan"] == {"section_edit_map": {"SEC_001": {"section_id": "SEC_001"}}, "transition_map": {}, "timing_map": {}, "section_edits": []}
    assert "final_video" not in out.payload
    assert out.artifacts == ["synced-final.mp4"]


def test_rerender_loop_marks_unresolved_rerender_outcome_when_review_still_fails(monkeypatch):
    monkeypatch.setattr(
        "ai_mv.core.stages.rerender_loop.run_prepare_rerender",
        lambda stage_input: StageOutput(
            "prepare_rerender",
            "done",
            {"rerender_stage_sequence": ["stills"], "rerender_stage_inputs": {"stills": {"shot_plan": [], "render_plan": []}}},
            [],
        ),
    )
    monkeypatch.setattr(
        "ai_mv.core.stages.rerender_loop.run_repair_rerender_prompts",
        lambda stage_input: StageOutput("repair_rerender_prompts", "done", {"rerender_stage_inputs": {"stills": {"shot_plan": [], "render_plan": []}}}, []),
    )
    monkeypatch.setattr(
        "ai_mv.core.stages.rerender_loop.run_execute_rerender",
        lambda stage_input: StageOutput("execute_rerender", "done", {"rerender_results": {"completed_stages": ["stills"], "still_results": [], "clip_results": []}}, []),
    )
    monkeypatch.setattr(
        "ai_mv.core.stages.rerender_loop.run_rerender_review",
        lambda stage_input: StageOutput(
            "rerender_review",
            "done",
            {
                "rerender_review_report": {"status": "needs_rerender", "rerender_targets": ["S009"]},
                "still_results": [],
                "clip_results": [],
            },
            [],
        ),
    )

    out = run_rerender_loop(StageInput(run_id="run-rerender-loop-fail", config={}, payload={"review_report": {"status": "needs_rerender"}}))

    assert out.payload["rerender_review_report"] == {"status": "needs_rerender", "rerender_targets": ["S009"]}
    assert "review_report" not in out.payload
    assert out.payload["rerender_outcome"] == {"attempted": True, "resolved": False, "exhausted": True}



def test_rerender_escalation_builds_manual_review_packet_request(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        "ai_mv.core.stages.rerender_escalation.write_review_packet",
        lambda **kwargs: (
            captured.update(kwargs) or {
                "manifest_path": kwargs["output_dir"] / "review-packet.json",
                "quality_findings_path": kwargs["output_dir"] / "review-findings.json",
                "reviewer_notes_path": kwargs["output_dir"] / "review-notes.md",
                "contact_sheet_image_path": kwargs["output_dir"] / "contact-sheet.png",
                "contact_sheet_manifest_path": kwargs["output_dir"] / "contact-sheet.json",
            }
        ),
    )

    out = run_rerender_escalation(
        StageInput(
            run_id="run-rerender-escalate-1",
            config={},
            payload={
                "final_video": "D:/renders/final.mp4",
                "review_report": {
                    "rerender_targets": ["S003", "S007"],
                    "rerender_reasons": {
                        "S003": ["continuity_break", "identity_drift"],
                        "S007": ["terminal_frame_corruption"],
                    },
                    "rerender_bundle": {
                        "action": "rerender_continuity_break_shots",
                        "target_shots": ["S003"],
                        "target_material_ids": ["MAT_003"],
                        "target_section_ids": ["SEC_003"],
                        "reason_codes": ["continuity_break", "identity_drift"],
                    },
                    "rerender_execution_payloads": [
                        {
                            "shot_id": "S003",
                            "recommended_action": "rerender_continuity_break_shots",
                            "rerender_stage": "review",
                            "stage_payloads": {
                                "review": {
                                    "final_video": "D:/renders/final.mp4",
                                    "music_file": "song.mp3",
                                    "recommended_action": "rerender_continuity_break_shots",
                                    "target_shots": ["S003"],
                                    "target_material_ids": ["MAT_003"],
                                    "target_section_ids": ["SEC_003"],
                                }
                            },
                        },
                        {
                            "shot_id": "S007",
                            "recommended_action": "rerender_clips_with_terminal_frame_cleanup",
                            "rerender_stage": "clips",
                            "stage_payloads": {
                                "clips": {
                                    "shot_plan": [{"shot_id": "S007", "material_id": "MAT_007", "section_id": "SEC_007"}],
                                    "render_plan": [
                                        {
                                            "shot_id": "S007",
                                            "material_id": "MAT_007",
                                            "section_id": "SEC_007",
                                            "render_mode": "ia2v",
                                            "reference_mode": "use_performance_anchor_still",
                                            "reference_source_shot_id": "S006",
                                            "identity_lock_strength": "performance_anchor",
                                            "edit_variation_scope": "performance_pose_upgrade",
                                            "minimum_visual_delta": "facial_expression_shift",
                                        }
                                    ],
                                    "still_results": [{"shot_id": "S007", "material_id": "MAT_007", "section_id": "SEC_007", "image": "still-7.png"}],
                                    "music_file": "song.mp3",
                                }
                            },
                        },
                    ],
                    "rerender_plan": [
                        {
                            "shot_id": "S003",
                            "priority_score": 9,
                            "recommended_action": "rerender_continuity_break_shots",
                            "rerender_prescription": {
                                "stage_focus": "review",
                                "workflow_focus": None,
                                "prompt_contract_focus": [],
                                "fix_strategy": "inspect_review_failures_manually",
                            },
                        },
                        {
                            "shot_id": "S007",
                            "priority_score": 5,
                            "recommended_action": "rerender_clips_with_terminal_frame_cleanup",
                            "rerender_prescription": {
                                "stage_focus": "clips",
                                "workflow_focus": ["ia2v"],
                                "prompt_contract_focus": ["clip_prompt_seed", "clip_positive_prompt"],
                                "fix_strategy": "shorter_motion_and_clean_terminal_frames",
                            },
                        },
                    ],
                },
                "rerender_outcome": {"attempted": True, "resolved": False, "exhausted": True},
            },
        )
    )

    report = out.payload["rerender_escalation"]
    assert report["status"] == "manual_review_required"
    assert report["shot_ids"] == ["S003", "S007"]
    assert report["material_ids"] == ["MAT_003", "MAT_007"]
    assert report["section_ids"] == ["SEC_003", "SEC_007"]
    assert report["shot_count"] == 2
    assert report["summary_by_shot"] == [
        {
            "shot_id": "S003",
            "material_id": "MAT_003",
            "section_id": "SEC_003",
            "reason_codes": ["continuity_break", "identity_drift"],
            "priority_score": 9,
            "recommended_action": "rerender_continuity_break_shots",
            "rerender_prescription": {
                "stage_focus": "review",
                "workflow_focus": None,
                "prompt_contract_focus": [],
                "fix_strategy": "inspect_review_failures_manually",
            },
            "reference_context": {
                "reference_mode": "",
                "reference_source_shot_id": "",
                "identity_lock_strength": "",
                "edit_variation_scope": "",
                "minimum_visual_delta": "",
            },
            "reference_summary_label": "",
            "packet_artifacts": report["artifacts"],
            "reviewer_note": "Inspect shot S003 in the review packet artifacts (reasons: continuity_break, identity_drift)",
        },
        {
            "shot_id": "S007",
            "material_id": "MAT_007",
            "section_id": "SEC_007",
            "reason_codes": ["terminal_frame_corruption"],
            "priority_score": 5,
            "recommended_action": "rerender_clips_with_terminal_frame_cleanup",
            "rerender_prescription": {
                "stage_focus": "clips",
                "workflow_focus": ["ia2v"],
                "prompt_contract_focus": ["clip_prompt_seed", "clip_positive_prompt"],
                "fix_strategy": "shorter_motion_and_clean_terminal_frames",
            },
            "reference_context": {
                "reference_mode": "use_performance_anchor_still",
                "reference_source_shot_id": "S006",
                "identity_lock_strength": "performance_anchor",
                "edit_variation_scope": "performance_pose_upgrade",
                "minimum_visual_delta": "facial_expression_shift",
            },
            "reference_summary_label": "performance follow-up from S006",
            "packet_artifacts": report["artifacts"],
            "reviewer_note": "Inspect shot S007 (performance follow-up from S006) in the review packet artifacts (reasons: terminal_frame_corruption)",
        },
    ]
    assert report["video_path"] == "D:/renders/final.mp4"
    assert report["reviewer_summary"] == "Manual review required for 2 shots across 2 materials and 2 sections: S003, S007"
    assert report["review_packet_manifest_path"].endswith("review-packet.json")
    assert report["quality_findings_path"].endswith("review-findings.json")
    assert report["reviewer_notes_path"].endswith("review-notes.md")
    assert report["contact_sheet_image_path"].endswith("contact-sheet.png")
    assert report["contact_sheet_manifest_path"].endswith("contact-sheet.json")
    assert report["artifacts"] == {
        "review_packet_manifest": report["review_packet_manifest_path"],
        "quality_findings": report["quality_findings_path"],
        "reviewer_notes": report["reviewer_notes_path"],
        "contact_sheet_image": report["contact_sheet_image_path"],
        "contact_sheet_manifest": report["contact_sheet_manifest_path"],
    }
    assert captured["escalation_context"] == {
        "source_stage": "rerender_escalation",
        "run_id": "run-rerender-escalate-1",
        "status": "manual_review_required",
        "shot_ids": ["S003", "S007"],
        "material_ids": ["MAT_003", "MAT_007"],
        "section_ids": ["SEC_003", "SEC_007"],
        "reference_modes": ["use_performance_anchor_still"],
        "anchor_source_shot_ids": [],
        "followup_shot_ids": ["S007"],
    }
    assert out.artifacts == [
        report["review_packet_manifest_path"],
        report["quality_findings_path"],
        report["reviewer_notes_path"],
        report["contact_sheet_image_path"],
        report["contact_sheet_manifest_path"],
    ]



def test_rerender_escalation_maps_batched_review_targets_to_their_own_provenance(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        "ai_mv.core.stages.rerender_escalation.write_review_packet",
        lambda **kwargs: (
            captured.update(kwargs) or {
                "manifest_path": kwargs["output_dir"] / "review-packet.json",
                "quality_findings_path": kwargs["output_dir"] / "review-findings.json",
                "reviewer_notes_path": kwargs["output_dir"] / "review-notes.md",
                "contact_sheet_image_path": kwargs["output_dir"] / "contact-sheet.png",
                "contact_sheet_manifest_path": kwargs["output_dir"] / "contact-sheet.json",
            }
        ),
    )

    out = run_rerender_escalation(
        StageInput(
            run_id="run-rerender-escalate-batched-review-targets",
            config={},
            payload={
                "final_video": "D:/renders/final.mp4",
                "review_report": {
                    "rerender_targets": ["S001", "S002", "S003"],
                    "rerender_reasons": {
                        "S001": ["excessive_sync_clone_tail"],
                        "S002": ["excessive_sync_clone_tail"],
                        "S003": ["excessive_sync_clone_tail"],
                    },
                    "rerender_execution_payloads": [
                        {
                            "shot_id": "S001",
                            "recommended_action": "revise_assembly_coverage_before_sync_pad",
                            "rerender_stage": "review",
                            "stage_payloads": {
                                "review": {
                                    "target_shots": ["S001", "S002", "S003"],
                                    "target_material_ids": ["MAT_001", "MAT_002", "MAT_003"],
                                    "target_section_ids": ["SEC_001", "SEC_002", "SEC_003"],
                                }
                            },
                        }
                    ],
                    "rerender_plan": [
                        {"shot_id": "S001", "priority_score": 4, "recommended_action": "revise_assembly_coverage_before_sync_pad"},
                        {"shot_id": "S002", "priority_score": 4, "recommended_action": "revise_assembly_coverage_before_sync_pad"},
                        {"shot_id": "S003", "priority_score": 4, "recommended_action": "revise_assembly_coverage_before_sync_pad"},
                    ],
                },
                "rerender_outcome": {"attempted": True, "resolved": False, "exhausted": True},
            },
        )
    )

    report = out.payload["rerender_escalation"]
    assert report["material_ids"] == ["MAT_001", "MAT_002", "MAT_003"]
    assert report["section_ids"] == ["SEC_001", "SEC_002", "SEC_003"]
    assert [(row["shot_id"], row["material_id"], row["section_id"]) for row in report["summary_by_shot"]] == [
        ("S001", "MAT_001", "SEC_001"),
        ("S002", "MAT_002", "SEC_002"),
        ("S003", "MAT_003", "SEC_003"),
    ]
    assert report["reviewer_summary"] == "Manual review required for 3 shots across 3 materials and 3 sections: S001, S002, S003"
    assert captured["escalation_context"]["material_ids"] == ["MAT_001", "MAT_002", "MAT_003"]
    assert captured["escalation_context"]["section_ids"] == ["SEC_001", "SEC_002", "SEC_003"]



def test_rerender_escalation_reviewer_summary_uses_unique_material_and_section_counts(monkeypatch):
    monkeypatch.setattr(
        "ai_mv.core.stages.rerender_escalation.write_review_packet",
        lambda **kwargs: {
            "manifest_path": kwargs["output_dir"] / "review-packet.json",
            "quality_findings_path": kwargs["output_dir"] / "review-findings.json",
            "reviewer_notes_path": kwargs["output_dir"] / "review-notes.md",
            "contact_sheet_image_path": kwargs["output_dir"] / "contact-sheet.png",
            "contact_sheet_manifest_path": kwargs["output_dir"] / "contact-sheet.json",
        },
    )

    out = run_rerender_escalation(
        StageInput(
            run_id="run-rerender-escalate-shared-provenance",
            config={},
            payload={
                "final_video": "D:/renders/final.mp4",
                "review_report": {
                    "rerender_targets": ["S003", "S004"],
                    "rerender_reasons": {
                        "S003": ["continuity_break"],
                        "S004": ["continuity_break"],
                    },
                    "rerender_execution_payloads": [
                        {
                            "shot_id": "S003",
                            "stage_payloads": {
                                "review": {
                                    "target_shots": ["S003"],
                                    "target_material_ids": ["MAT_SHARED"],
                                    "target_section_ids": ["SEC_SHARED"],
                                }
                            },
                        },
                        {
                            "shot_id": "S004",
                            "stage_payloads": {
                                "review": {
                                    "target_shots": ["S004"],
                                    "target_material_ids": ["MAT_SHARED"],
                                    "target_section_ids": ["SEC_SHARED"],
                                }
                            },
                        },
                    ],
                },
                "rerender_outcome": {"attempted": True, "resolved": False, "exhausted": True},
            },
        )
    )

    assert out.payload["rerender_escalation"]["material_ids"] == ["MAT_SHARED"]
    assert out.payload["rerender_escalation"]["section_ids"] == ["SEC_SHARED"]
    assert out.payload["rerender_escalation"]["reviewer_summary"] == "Manual review required for 2 shots across 1 materials and 1 sections: S003, S004"



def test_rerender_escalation_skips_packet_creation_when_not_exhausted(monkeypatch):
    called = []
    monkeypatch.setattr(
        "ai_mv.core.stages.rerender_escalation.write_review_packet",
        lambda **kwargs: called.append(True),
    )

    out = run_rerender_escalation(
        StageInput(
            run_id="run-rerender-escalate-2",
            config={},
            payload={
                "final_video": "D:/renders/final.mp4",
                "review_report": {"rerender_targets": ["S003"]},
                "rerender_outcome": {"attempted": True, "resolved": True, "exhausted": False},
            },
        )
    )

    assert called == []
    assert out.payload["rerender_escalation"] == {
        "status": "not_required",
        "shot_ids": [],
        "material_ids": [],
        "section_ids": [],
        "shot_count": 0,
        "summary_by_shot": [],
        "video_path": "D:/renders/final.mp4",
        "reviewer_summary": "No manual review required",
        "artifacts": {},
    }



def test_rerender_loop_returns_original_payload_when_no_rerender_targets_exist(monkeypatch):
    seen_prepare = []

    def _fake_prepare(stage_input):
        seen_prepare.append(True)
        return StageOutput("prepare_rerender", "done", {"rerender_stage_sequence": [], "rerender_stage_inputs": {}}, [])

    monkeypatch.setattr("ai_mv.core.stages.rerender_loop.run_prepare_rerender", _fake_prepare)

    out = run_rerender_loop(
        StageInput(
            run_id="run-rerender-loop-empty",
            config={},
            payload={"review_report": {"rerender_execution_payloads": []}, "still_results": [{"shot_id": "S001"}]},
        )
    )

    assert seen_prepare == [True]
    assert out.payload["rerender_stage_inputs"] == {}
    assert out.payload["rerender_stage_sequence"] == []
    assert out.payload["still_results"] == [{"shot_id": "S001"}]
