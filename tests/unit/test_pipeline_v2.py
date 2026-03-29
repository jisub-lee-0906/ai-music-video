from ai_mv.core.contracts.stage_io import StageOutput
from ai_mv.core.orchestration import pipeline_v2


def test_pipeline_v2_runs_ordered_stages(monkeypatch):
    order: list[str] = []

    monkeypatch.setattr(pipeline_v2, "init_run_state", lambda cfg, run_id, allow_existing=False: {"run_id": run_id or "v2", "status": "running"})
    monkeypatch.setattr(pipeline_v2, "save_snapshot", lambda state, payload: None)
    monkeypatch.setattr(pipeline_v2, "write_pipeline_artifacts", lambda state, payload, cfg: None)
    monkeypatch.setattr(pipeline_v2, "build_director_brief_intent", lambda cfg: {"title": "x"})
    monkeypatch.setattr(pipeline_v2, "validate_stage_input", lambda stage, payload: None)

    def fake_run_result_stage(state, stage_input, name, stage_fn, save_snapshot, validate_stage_input):
        order.append(name)
        stage_output = stage_fn(stage_input)
        assert isinstance(stage_output, StageOutput)
        stage_input.payload.update(stage_output.payload)
        return True

    monkeypatch.setattr(pipeline_v2, "run_result_stage", fake_run_result_stage)

    def _stage(name, payload):
        return lambda stage_input: StageOutput(name, "done", payload)

    monkeypatch.setattr(pipeline_v2, "run_acestep_music", _stage("acestep_music", {"audio_plan": {"genre_description": "x"}, "audio_map": {"sections": [{"name": "verse"}]}, "music_file": "music.mp3"}))
    monkeypatch.setattr(pipeline_v2, "run_lyrics_timeline", _stage("lyrics_timeline", {"lyrics_timeline": {"sections": [{"section_name": "Verse 1", "lyric_beats": [{"beat_id": "b1", "start_sec": 0.0, "end_sec": 2.0, "visible_action": "looks up"}]}]}}))
    monkeypatch.setattr(pipeline_v2, "run_scene_plan_v2", _stage("scene_plan_v2", {"scene_plan_v2": {"shot_packages": [{"shot_id": "b1"}]}}))
    monkeypatch.setattr(pipeline_v2, "run_director_plan_v2", _stage("director_plan_v2", {"director_plan_v2": {"shot_packages": [{"shot_id": "b1"}]}}))
    monkeypatch.setattr(pipeline_v2, "run_render_plan_v2", _stage("render_plan_v2", {"render_plan_v2": {"shot_packages": [{"shot_id": "b1"}], "wan_chain": [{"shot_id": "b1", "camera_intent": "pushes in", "environment_anchor": "a wet station platform", "motion_intent": "hair shifts in wind"}]}}))
    monkeypatch.setattr(pipeline_v2, "run_backend_preview_v2", _stage("backend_preview_v2", {"backend_preview_v2": {"wan_prompt_preview": []}}))
    monkeypatch.setattr(pipeline_v2, "run_tti_anchor_v2", _stage("tti_anchor_v2", {"anchors": [{"shot_id": "b1", "identity_anchor": "anchor.png"}], "master_anchor_v2": "anchor.png"}))
    monkeypatch.setattr(pipeline_v2, "run_flux2_ref_chain_v2", _stage("flux2_ref_chain_v2", {"flux2_ref_images": [{"shot_id": "b1", "start": "start.png", "end": "end.png"}], "clip_routes": [{"shot_id": "b1", "anchor": "anchor.png", "duration_sec": 2.0, "section_name": "Verse 1", "section_label": "Verse 1"}]}))
    monkeypatch.setattr(pipeline_v2, "run_wan_interpolation_v2", _stage("wan_interpolation_v2", {"clips": [{"shot_id": "b1", "video": "clip.mp4"}]}))
    monkeypatch.setattr(pipeline_v2, "run_merge_mux", _stage("merge_mux", {"final_video": "final.mp4"}))

    run_id = pipeline_v2.run_pipeline_v2({"brief": "director_brief_example"}, "seedance-test", allow_existing_run=True)

    assert run_id == "seedance-test"
    assert order == [
        "acestep_music",
        "lyrics_timeline",
        "scene_plan_v2",
        "director_plan_v2",
        "render_plan_v2",
        "backend_preview_v2",
        "tti_anchor_v2",
        "flux2_ref_chain_v2",
        "wan_interpolation_v2",
        "merge_mux",
    ]

