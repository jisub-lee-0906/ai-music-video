from ai_mv.core.contracts.stage_io import StageOutput
from ai_mv.core.orchestration import pipeline


def test_pipeline_runs_ordered_stages(monkeypatch):
    order: list[str] = []

    monkeypatch.setattr(pipeline, "init_run_state", lambda cfg, run_id, allow_existing=False: {"run_id": run_id or "run-123", "status": "running"})
    monkeypatch.setattr(pipeline, "save_snapshot", lambda state, payload: None)
    monkeypatch.setattr(pipeline, "write_pipeline_artifacts", lambda state, payload, cfg: None)
    monkeypatch.setattr(pipeline, "build_director_brief_intent", lambda cfg: {"title": "x"})
    monkeypatch.setattr(pipeline, "validate_stage_input", lambda stage, payload: None)

    def fake_run_result_stage(state, stage_input, name, stage_fn, save_snapshot, validate_stage_input):
        order.append(name)
        stage_output = stage_fn(stage_input)
        assert isinstance(stage_output, StageOutput)
        stage_input.payload.update(stage_output.payload)
        return True

    monkeypatch.setattr(pipeline, "run_result_stage", fake_run_result_stage)

    def _stage(name, payload):
        return lambda stage_input: StageOutput(name, "done", payload)

    monkeypatch.setattr(pipeline, "run_acestep_music", _stage("acestep_music", {"audio_plan": {"genre_description": "x"}, "audio_map": {"sections": [{"name": "verse"}]}, "music_file": "music.mp3"}))
    monkeypatch.setattr(pipeline, "run_lyrics_timeline", _stage("lyrics_timeline", {"lyrics_timeline": {"sections": [{"section_name": "Verse 1", "lyric_beats": [{"beat_id": "b1", "start_sec": 0.0, "end_sec": 2.0, "visible_action": "looks up"}]}]}}))
    monkeypatch.setattr(pipeline, "run_scene_plan", _stage("scene_plan", {"scene_plan": {"shot_packages": [{"shot_id": "b1"}]}}))
    monkeypatch.setattr(pipeline, "run_director_plan", _stage("director_plan", {"director_plan": {"shot_packages": [{"shot_id": "b1"}]}}))
    monkeypatch.setattr(pipeline, "run_render_plan", _stage("render_plan", {"render_plan": {"shot_packages": [{"shot_id": "b1"}], "wan_chain": [{"shot_id": "b1", "camera_intent": "pushes in", "environment_anchor": "a wet station platform", "motion_intent": "hair shifts in wind"}]}}))
    monkeypatch.setattr(pipeline, "run_backend_preview", _stage("backend_preview", {"backend_preview": {"wan_prompt_preview": []}}))
    monkeypatch.setattr(pipeline, "run_tti_anchor", _stage("tti_anchor", {"anchors": [{"shot_id": "b1", "identity_anchor": "anchor.png"}], "master_anchor": "anchor.png"}))
    monkeypatch.setattr(pipeline, "run_flux2_ref_chain", _stage("flux2_ref_chain", {"flux2_ref_images": [{"shot_id": "b1", "start": "start.png", "end": "end.png"}], "clip_routes": [{"shot_id": "b1", "anchor": "anchor.png", "duration_sec": 2.0, "section_name": "Verse 1", "section_label": "Verse 1"}]}))
    monkeypatch.setattr(pipeline, "run_wan_interpolation", _stage("wan_interpolation", {"clips": [{"shot_id": "b1", "video": "clip.mp4"}]}))
    monkeypatch.setattr(pipeline, "run_merge_mux", _stage("merge_mux", {"final_video": "final.mp4"}))

    run_id = pipeline.run_pipeline({"brief": "director_brief_example"}, "visual-test", allow_existing_run=True)

    assert run_id == "visual-test"
    assert order == [
        "acestep_music",
        "lyrics_timeline",
        "scene_plan",
        "director_plan",
        "render_plan",
        "backend_preview",
        "tti_anchor",
        "flux2_ref_chain",
        "wan_interpolation",
        "merge_mux",
    ]

