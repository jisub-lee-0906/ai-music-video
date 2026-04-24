from pathlib import Path

import ai_mv.entrypoints.audio_reroll_start as entry



def test_run_audio_reroll_start_uses_latest_success_concept_and_rubric(monkeypatch, capsys):
    seen = {}
    monkeypatch.setattr(entry, "acquire_lock", lambda _name: object())
    monkeypatch.setattr(entry, "release_lock", lambda _lock: None)
    monkeypatch.setattr(entry, "latest_success_file", lambda name, scope="run": Path(f"/tmp/{scope}/{name}"))
    monkeypatch.setattr(entry, "read_json", lambda path: {"input": {"concept_text": "citypop night drive"}})

    def _fake_load(concept_text):
        seen["concept_text"] = concept_text
        return {"concept_text": concept_text, "review": {}}

    def _fake_prepare_queue(cfg):
        seen["queue_cfg"] = cfg

    def _fake_prepare(cfg, run_id):
        seen["prepared"] = (cfg, run_id)
        return "reroll-start-123"

    def _fake_run_pipeline(cfg, rid, allow_existing_run=True):
        seen["pipeline"] = (cfg, rid, allow_existing_run)
        return rid

    monkeypatch.setattr(entry, "_load_prepared_config", _fake_load)
    monkeypatch.setattr(entry, "_prepare_comfy_queue", _fake_prepare_queue)
    monkeypatch.setattr(entry, "_prepare_run_brief", _fake_prepare)
    monkeypatch.setattr(entry, "run_doctor", lambda _cfg: 0)
    monkeypatch.setattr(entry, "run_pipeline", _fake_run_pipeline)
    monkeypatch.setattr(entry, "read_snapshot", lambda _rid: {"status": "done", "failure_reason": ""})

    rc = entry.run_audio_reroll_start(
        rubric_path="/tmp/audio-review-rubric-reviewed.json",
        run_id="reroll-start-123",
        concept_text=None,
        scope="run",
    )
    out = capsys.readouterr().out

    assert rc == 0
    assert seen["concept_text"] == "citypop night drive"
    assert seen["prepared"][0]["review"]["audio_review_rubric_path"] == "/tmp/audio-review-rubric-reviewed.json"
    assert seen["pipeline"][1] == "reroll-start-123"
    assert "run_id=reroll-start-123" in out
    assert "status=done" in out
    assert "rubric_path=/tmp/audio-review-rubric-reviewed.json" in out



def test_run_audio_reroll_start_prefers_explicit_concept_text(monkeypatch, capsys):
    seen = {}
    monkeypatch.setattr(entry, "acquire_lock", lambda _name: object())
    monkeypatch.setattr(entry, "release_lock", lambda _lock: None)
    monkeypatch.setattr(entry, "latest_success_file", lambda name, scope="run": Path(f"/tmp/{scope}/{name}"))
    monkeypatch.setattr(entry, "read_json", lambda path: {"input": {"concept_text": "citypop night drive"}})

    def _fake_load(concept_text):
        seen["concept_text"] = concept_text
        return {"concept_text": concept_text, "review": {}}

    monkeypatch.setattr(entry, "_load_prepared_config", _fake_load)
    monkeypatch.setattr(entry, "run_doctor", lambda _cfg: 0)
    monkeypatch.setattr(entry, "_prepare_comfy_queue", lambda _cfg: None)
    monkeypatch.setattr(entry, "_prepare_run_brief", lambda cfg, run_id: "reroll-start-456")
    monkeypatch.setattr(entry, "run_pipeline", lambda cfg, rid, allow_existing_run=True: rid)
    monkeypatch.setattr(entry, "read_snapshot", lambda _rid: {"status": "done", "failure_reason": ""})

    rc = entry.run_audio_reroll_start(
        rubric_path="/tmp/audio-review-rubric-reviewed.json",
        run_id="reroll-start-456",
        concept_text="explicit override concept",
        scope="run",
    )
    out = capsys.readouterr().out

    assert rc == 0
    assert seen["concept_text"] == "explicit override concept"
    assert "run_id=reroll-start-456" in out



def test_run_audio_reroll_start_threads_latest_success_style_lane_into_default_style_name(monkeypatch, capsys):
    seen = {}
    monkeypatch.setattr(entry, "acquire_lock", lambda _name: object())
    monkeypatch.setattr(entry, "release_lock", lambda _lock: None)
    monkeypatch.setattr(entry, "latest_success_file", lambda name, scope="run": Path(f"/tmp/{scope}/{name}"))
    monkeypatch.setattr(
        entry,
        "read_json",
        lambda path: {
            "input": {"concept_text": "late-night city walk under wet neon lights with one protagonist moving through the same boulevard world"},
            "plan": {"style_lane": "citypop"},
        },
    )

    def _fake_load(concept_text):
        seen["concept_text"] = concept_text
        return {"concept_text": concept_text, "review": {}, "planning": {}}

    def _fake_prepare(cfg, run_id):
        seen["prepared_cfg"] = cfg
        return "reroll-start-789"

    monkeypatch.setattr(entry, "_load_prepared_config", _fake_load)
    monkeypatch.setattr(entry, "run_doctor", lambda _cfg: 0)
    monkeypatch.setattr(entry, "_prepare_comfy_queue", lambda _cfg: None)
    monkeypatch.setattr(entry, "_prepare_run_brief", _fake_prepare)
    monkeypatch.setattr(entry, "run_pipeline", lambda cfg, rid, allow_existing_run=True: rid)
    monkeypatch.setattr(entry, "read_snapshot", lambda _rid: {"status": "done", "failure_reason": ""})

    rc = entry.run_audio_reroll_start(
        rubric_path="/tmp/audio-review-rubric-reviewed.json",
        run_id="reroll-start-789",
        concept_text=None,
        scope="run",
    )
    out = capsys.readouterr().out

    assert rc == 0
    assert seen["concept_text"].startswith("late-night city walk")
    assert "run_id=reroll-start-789" in out
    assert seen["prepared_cfg"]["planning"]["default_style_name"] == "citypop"



def test_run_audio_reroll_start_does_not_require_latest_success_when_explicit_concept_text_is_provided(monkeypatch, capsys):
    seen = {}
    monkeypatch.setattr(entry, "acquire_lock", lambda _name: object())
    monkeypatch.setattr(entry, "release_lock", lambda _lock: None)

    def _boom(*_args, **_kwargs):
        raise AssertionError("latest_success should not be read when explicit concept_text is provided")

    def _fake_load(concept_text):
        seen["concept_text"] = concept_text
        return {"concept_text": concept_text, "review": {}, "planning": {}}

    monkeypatch.setattr(entry, "latest_success_file", _boom)
    monkeypatch.setattr(entry, "read_json", _boom)
    monkeypatch.setattr(entry, "_load_prepared_config", _fake_load)
    monkeypatch.setattr(entry, "run_doctor", lambda _cfg: 0)
    monkeypatch.setattr(entry, "_prepare_comfy_queue", lambda _cfg: None)
    monkeypatch.setattr(entry, "_prepare_run_brief", lambda cfg, run_id: "reroll-start-explicit")
    monkeypatch.setattr(entry, "run_pipeline", lambda cfg, rid, allow_existing_run=True: rid)
    monkeypatch.setattr(entry, "read_snapshot", lambda _rid: {"status": "done", "failure_reason": ""})

    rc = entry.run_audio_reroll_start(
        rubric_path="/tmp/audio-review-rubric-reviewed.json",
        run_id="reroll-start-explicit",
        concept_text="explicit override concept",
        scope="run",
    )
    out = capsys.readouterr().out

    assert rc == 0
    assert seen["concept_text"] == "explicit override concept"
    assert "run_id=reroll-start-explicit" in out
