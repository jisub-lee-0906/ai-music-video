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
        ("plan", _stage("plan", {
            "citypop_bible": {"style": "citypop"},
            "shot_plan": [{"shot_id": "S001", "start_sec": 0.0, "end_sec": 4.0}],
            "render_plan": [{"shot_id": "S001", "render_mode": "i2v"}],
        })),
        ("stills", _stage("stills", {
            "still_results": [{"shot_id": "S001", "image": "stills/S001.png"}],
        })),
        ("clips", _stage("clips", {"clip_results": [{"shot_id": "S001", "video": "clips/S001_i2v.mp4"}]})),
        ("assemble", _stage("assemble", {"final_video": "final.mp4", "review_inputs": {"music_file": "music.mp3"}})),
        ("review", _stage("review", {"review_report": {"status": "ok"}})),
    ])

    run_id = pipeline.run_pipeline({"concept_text": "citypop night drive"}, "visual-test", allow_existing_run=True)

    assert run_id == "visual-test"
    assert order == [
        "audio",
        "plan",
        "stills",
        "clips",
        "assemble",
        "review",
    ]
