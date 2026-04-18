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
            "style_bible": {"style": "citypop"},
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



def test_pipeline_runs_rerender_loop_when_review_needs_rerender(monkeypatch):
    order: list[str] = []
    final_payload: dict = {}

    monkeypatch.setattr(
        pipeline,
        "init_run_state",
        lambda cfg, run_id, allow_existing=False: {
            "run_id": run_id or "run-rerender",
            "status": "running",
            "current_stage": "",
            "failure_reason": "",
            "completed_stages": [],
        },
    )
    monkeypatch.setattr(pipeline, "save_snapshot", lambda state, payload: None)
    monkeypatch.setattr(
        pipeline,
        "write_pipeline_artifacts",
        lambda state, payload, cfg: final_payload.update(payload),
    )
    monkeypatch.setattr(pipeline, "validate_stage_input", lambda stage, payload: None)

    def fake_run_result_stage(state, stage_input, name, stage_fn, save_snapshot, validate_stage_input):
        order.append(name)
        stage_output = stage_fn(stage_input)
        assert isinstance(stage_output, StageOutput)
        stage_input.payload.update(stage_output.payload)
        state["completed_stages"].append(name)
        return True

    monkeypatch.setattr(pipeline, "run_result_stage", fake_run_result_stage)

    def _stage(name, payload):
        return lambda stage_input: StageOutput(name, "done", payload)

    monkeypatch.setattr(pipeline, "_ordered_stages", lambda: [
        ("audio", _stage("audio", {"audio_plan": {"genre_description": "x"}, "audio_map": {"sections": [{"name": "verse"}]}, "music_file": "music.mp3"})),
        ("plan", _stage("plan", {
            "style_bible": {"style": "citypop"},
            "shot_plan": [{"shot_id": "S001", "start_sec": 0.0, "end_sec": 4.0}],
            "render_plan": [{"shot_id": "S001", "render_mode": "i2v"}],
        })),
        ("stills", _stage("stills", {"still_results": [{"shot_id": "S001", "image": "stills/S001.png"}]})),
        ("clips", _stage("clips", {"clip_results": [{"shot_id": "S001", "video": "clips/S001_i2v.mp4"}]})),
        ("assemble", _stage("assemble", {"final_video": "final.mp4", "review_inputs": {"music_file": "music.mp3"}})),
        ("review", _stage("review", {"review_report": {"status": "needs_rerender", "rerender_execution_payloads": [{"shot_id": "S001"}]}})),
    ])
    monkeypatch.setattr(
        pipeline,
        "run_rerender_loop",
        lambda stage_input: StageOutput(
            "rerender_loop",
            "done",
            {
                "review_report": {"status": "done", "rerender_targets": []},
                "rerender_review_report": {"status": "done", "rerender_targets": []},
                "rerender_results": {"completed_stages": ["stills"]},
            },
        ),
    )

    run_id = pipeline.run_pipeline({"concept_text": "citypop night drive"}, "rerender-test", allow_existing_run=True)

    assert run_id == "rerender-test"
    assert order == ["audio", "plan", "stills", "clips", "assemble", "review", "rerender"]
    assert final_payload["review_report"] == {"status": "done", "rerender_targets": []}
    assert final_payload["rerender_results"] == {"completed_stages": ["stills"]}
    assert final_payload["rerender_outcome"] == {"attempted": True, "resolved": True, "exhausted": False}



def test_pipeline_marks_unresolved_rerender_outcome_when_loop_still_needs_rerender(monkeypatch):
    final_payload: dict = {}

    monkeypatch.setattr(
        pipeline,
        "init_run_state",
        lambda cfg, run_id, allow_existing=False: {
            "run_id": run_id or "run-rerender-fail",
            "status": "running",
            "current_stage": "",
            "failure_reason": "",
            "completed_stages": [],
        },
    )
    monkeypatch.setattr(pipeline, "save_snapshot", lambda state, payload: None)
    monkeypatch.setattr(pipeline, "write_pipeline_artifacts", lambda state, payload, cfg: final_payload.update(payload))
    monkeypatch.setattr(pipeline, "validate_stage_input", lambda stage, payload: None)

    def fake_run_result_stage(state, stage_input, name, stage_fn, save_snapshot, validate_stage_input):
        stage_output = stage_fn(stage_input)
        stage_input.payload.update(stage_output.payload)
        state["completed_stages"].append(name)
        return True

    monkeypatch.setattr(pipeline, "run_result_stage", fake_run_result_stage)

    def _stage(name, payload):
        return lambda stage_input: StageOutput(name, "done", payload)

    monkeypatch.setattr(pipeline, "_ordered_stages", lambda: [
        ("audio", _stage("audio", {"audio_plan": {"genre_description": "x"}, "audio_map": {"sections": [{"name": "verse"}]}, "music_file": "music.mp3"})),
        ("plan", _stage("plan", {"style_bible": {"style": "citypop"}, "shot_plan": [{"shot_id": "S001"}], "render_plan": [{"shot_id": "S001", "render_mode": "i2v"}]})),
        ("stills", _stage("stills", {"still_results": [{"shot_id": "S001", "image": "stills/S001.png"}]})),
        ("clips", _stage("clips", {"clip_results": [{"shot_id": "S001", "video": "clips/S001_i2v.mp4"}]})),
        ("assemble", _stage("assemble", {"final_video": "final.mp4", "review_inputs": {"music_file": "music.mp3"}})),
        ("review", _stage("review", {"review_report": {"status": "needs_rerender", "rerender_targets": ["S001"]}})),
    ])
    monkeypatch.setattr(
        pipeline,
        "run_rerender_loop",
        lambda stage_input: StageOutput(
            "rerender_loop",
            "done",
            {
                "review_report": {"status": "needs_rerender", "rerender_targets": ["S001"]},
                "rerender_review_report": {"status": "needs_rerender", "rerender_targets": ["S001"]},
                "rerender_outcome": {"attempted": True, "resolved": False, "exhausted": True},
            },
        ),
    )
    monkeypatch.setattr(
        pipeline,
        "run_rerender_escalation",
        lambda stage_input: StageOutput(
            "rerender_escalation",
            "done",
            {"rerender_escalation": {"status": "manual_review_required", "shot_ids": ["S001"], "video_path": "final.mp4"}},
        ),
    )

    pipeline.run_pipeline({"concept_text": "citypop night drive"}, "rerender-fail-test", allow_existing_run=True)

    assert final_payload["review_report"] == {"status": "needs_rerender", "rerender_targets": ["S001"]}
    assert final_payload["rerender_outcome"] == {"attempted": True, "resolved": False, "exhausted": True}



def test_pipeline_runs_escalation_after_exhausted_rerender(monkeypatch):
    order: list[str] = []
    final_payload: dict = {}

    monkeypatch.setattr(
        pipeline,
        "init_run_state",
        lambda cfg, run_id, allow_existing=False: {
            "run_id": run_id or "run-escalate",
            "status": "running",
            "current_stage": "",
            "failure_reason": "",
            "completed_stages": [],
        },
    )
    monkeypatch.setattr(pipeline, "save_snapshot", lambda state, payload: None)
    monkeypatch.setattr(pipeline, "write_pipeline_artifacts", lambda state, payload, cfg: final_payload.update(payload))
    monkeypatch.setattr(pipeline, "validate_stage_input", lambda stage, payload: None)

    def fake_run_result_stage(state, stage_input, name, stage_fn, save_snapshot, validate_stage_input):
        order.append(name)
        stage_output = stage_fn(stage_input)
        stage_input.payload.update(stage_output.payload)
        state["completed_stages"].append(name)
        return True

    monkeypatch.setattr(pipeline, "run_result_stage", fake_run_result_stage)

    def _stage(name, payload):
        return lambda stage_input: StageOutput(name, "done", payload)

    monkeypatch.setattr(pipeline, "_ordered_stages", lambda: [
        ("audio", _stage("audio", {"audio_plan": {"genre_description": "x"}, "audio_map": {"sections": [{"name": "verse"}]}, "music_file": "music.mp3"})),
        ("plan", _stage("plan", {"style_bible": {"style": "citypop"}, "shot_plan": [{"shot_id": "S001"}], "render_plan": [{"shot_id": "S001", "render_mode": "i2v"}]})),
        ("stills", _stage("stills", {"still_results": [{"shot_id": "S001", "image": "stills/S001.png"}]})),
        ("clips", _stage("clips", {"clip_results": [{"shot_id": "S001", "video": "clips/S001_i2v.mp4"}]})),
        ("assemble", _stage("assemble", {"final_video": "final.mp4", "review_inputs": {"music_file": "music.mp3"}})),
        ("review", _stage("review", {"review_report": {"status": "needs_rerender", "rerender_targets": ["S001"]}})),
    ])
    monkeypatch.setattr(
        pipeline,
        "run_rerender_loop",
        lambda stage_input: StageOutput(
            "rerender_loop",
            "done",
            {
                "review_report": {"status": "needs_rerender", "rerender_targets": ["S001"]},
                "rerender_review_report": {"status": "needs_rerender", "rerender_targets": ["S001"]},
                "rerender_outcome": {"attempted": True, "resolved": False, "exhausted": True},
            },
        ),
    )
    monkeypatch.setattr(
        pipeline,
        "run_rerender_escalation",
        lambda stage_input: StageOutput(
            "rerender_escalation",
            "done",
            {"rerender_escalation": {"status": "manual_review_required", "shot_ids": ["S001"], "video_path": "final.mp4"}},
        ),
    )

    pipeline.run_pipeline({"concept_text": "citypop night drive"}, "escalate-test", allow_existing_run=True)

    assert order == ["audio", "plan", "stills", "clips", "assemble", "review", "rerender", "escalation"]
    assert final_payload["rerender_escalation"] == {"status": "manual_review_required", "shot_ids": ["S001"], "video_path": "final.mp4"}



def test_pipeline_skips_rerender_loop_when_review_is_done(monkeypatch):
    order: list[str] = []

    monkeypatch.setattr(
        pipeline,
        "init_run_state",
        lambda cfg, run_id, allow_existing=False: {
            "run_id": run_id or "run-no-rerender",
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
        stage_input.payload.update(stage_output.payload)
        state["completed_stages"].append(name)
        return True

    monkeypatch.setattr(pipeline, "run_result_stage", fake_run_result_stage)

    def _stage(name, payload):
        return lambda stage_input: StageOutput(name, "done", payload)

    monkeypatch.setattr(pipeline, "_ordered_stages", lambda: [
        ("audio", _stage("audio", {"audio_plan": {"genre_description": "x"}, "audio_map": {"sections": [{"name": "verse"}]}, "music_file": "music.mp3"})),
        ("plan", _stage("plan", {"style_bible": {"style": "citypop"}, "shot_plan": [{"shot_id": "S001"}], "render_plan": [{"shot_id": "S001", "render_mode": "i2v"}]})),
        ("stills", _stage("stills", {"still_results": [{"shot_id": "S001", "image": "stills/S001.png"}]})),
        ("clips", _stage("clips", {"clip_results": [{"shot_id": "S001", "video": "clips/S001_i2v.mp4"}]})),
        ("assemble", _stage("assemble", {"final_video": "final.mp4", "review_inputs": {"music_file": "music.mp3"}})),
        ("review", _stage("review", {"review_report": {"status": "done", "rerender_targets": []}})),
    ])

    rerender_called = []
    monkeypatch.setattr(
        pipeline,
        "run_rerender_loop",
        lambda stage_input: rerender_called.append(True) or StageOutput("rerender_loop", "done", {}),
    )

    pipeline.run_pipeline({"concept_text": "citypop night drive"}, "no-rerender-test", allow_existing_run=True)

    assert order == ["audio", "plan", "stills", "clips", "assemble", "review"]
    assert rerender_called == []
