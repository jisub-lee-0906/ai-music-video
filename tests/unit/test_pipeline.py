from ai_mv.core.contracts.stage_io import StageOutput
from ai_mv.core.orchestration import pipeline


def test_pipeline_runs_ordered_stages(monkeypatch):
    order: list[str] = []

    monkeypatch.setattr(
        pipeline,
        "init_run_state",
        lambda cfg, run_id, allow_existing=False: {
            "run_id": run_id or "run-123",
            "status": "running",
            "current_stage": "",
            "failure_reason": "",
            "completed_stages": [],
        },
    )
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

    monkeypatch.setattr(pipeline, "_ordered_stages", lambda: [
        ("audio", _stage("audio", {"audio_plan": {"genre_description": "x"}, "audio_map": {"sections": [{"name": "verse"}]}, "music_file": "music.mp3"})),
        ("storyboard", _stage("storyboard", {
            "lyrics_timeline": {"sections": [{"section_name": "Verse 1", "lyric_beats": [{"beat_id": "b1", "start_sec": 0.0, "end_sec": 2.0}]}]},
            "scene_outline": {"shot_packages": [{"shot_id": "b1", "world_zone": "entry_zone", "story_function": "entry"}]},
            "direction_plan": {"shot_packages": [{"shot_id": "b1", "ref_style_tag": "entry_pass"}]},
            "prompt_plan": {"ref_items": [{"shot_id": "b1"}], "wan_items": []},
            "storyboard": {"shot_count": 1},
        })),
        ("keyframes", _stage("keyframes", {
            "anchors": [{"shot_id": "b1", "identity_anchor": "anchor.png"}],
            "master_anchor": "anchor.png",
            "flux2_ref_images": [{"shot_id": "b1", "start": "start.png", "end": "end.png"}],
            "clip_routes": [{"shot_id": "b1", "anchor": "anchor.png", "duration_sec": 2.0, "section_name": "Verse 1", "section_label": "Verse 1"}],
            "keyframes": {"reference_count": 1},
        })),
        ("clips", _stage("clips", {"clips": [{"shot_id": "b1", "video": "clip.mp4"}]})),
        ("merge", _stage("merge", {"final_video": "final.mp4"})),
    ])

    run_id = pipeline.run_pipeline({"brief": "director_brief_example"}, "visual-test", allow_existing_run=True)

    assert run_id == "visual-test"
    assert order == [
        "audio",
        "storyboard",
        "keyframes",
        "clips",
        "merge",
    ]
