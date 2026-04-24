from pathlib import Path

import ai_mv.entrypoints.audio_reroll as entry



def test_run_audio_reroll_preflight_uses_latest_success_concept_and_rubric(monkeypatch, capsys):
    seen = {}
    monkeypatch.setattr(entry, "acquire_lock", lambda _name: object())
    monkeypatch.setattr(entry, "release_lock", lambda _lock: None)
    monkeypatch.setattr(entry, "latest_success_file", lambda name, scope="run": Path(f"/tmp/{scope}/{name}"))
    monkeypatch.setattr(entry, "read_json", lambda path: {"input": {"concept_text": "citypop night drive"}})

    def _fake_load(concept_text):
        seen["concept_text"] = concept_text
        return {"concept_text": concept_text, "review": {}}

    def _fake_prepare(cfg, run_id):
        seen["prepared"] = (cfg, run_id)
        return "reroll-123"

    def _fake_preflight(cfg, rid, allow_existing_run=True):
        seen["preflight"] = (cfg, rid, allow_existing_run)
        return rid

    monkeypatch.setattr(entry, "_load_prepared_config", _fake_load)
    monkeypatch.setattr(entry, "_prepare_run_brief", _fake_prepare)
    monkeypatch.setattr(entry, "run_preflight", _fake_preflight)

    rc = entry.run_audio_reroll_preflight(
        rubric_path="/tmp/audio-review-rubric-reviewed.json",
        run_id="reroll-123",
        concept_text=None,
        scope="run",
    )
    out = capsys.readouterr().out

    assert rc == 0
    assert seen["concept_text"] == "citypop night drive"
    assert seen["prepared"][0]["review"]["audio_review_rubric_path"] == "/tmp/audio-review-rubric-reviewed.json"
    assert seen["preflight"][1] == "reroll-123"
    assert "run_id=reroll-123" in out
    assert "status=done" in out
    assert "rubric_path=/tmp/audio-review-rubric-reviewed.json" in out



def test_run_audio_reroll_preflight_prefers_explicit_concept_text(monkeypatch, capsys):
    seen = {}
    monkeypatch.setattr(entry, "acquire_lock", lambda _name: object())
    monkeypatch.setattr(entry, "release_lock", lambda _lock: None)
    monkeypatch.setattr(entry, "latest_success_file", lambda name, scope="run": Path(f"/tmp/{scope}/{name}"))
    monkeypatch.setattr(entry, "read_json", lambda path: {"input": {"concept_text": "citypop night drive"}})

    def _fake_load(concept_text):
        seen["concept_text"] = concept_text
        return {"concept_text": concept_text, "review": {}}

    monkeypatch.setattr(entry, "_load_prepared_config", _fake_load)
    monkeypatch.setattr(entry, "_prepare_run_brief", lambda cfg, run_id: "reroll-456")
    monkeypatch.setattr(entry, "run_preflight", lambda cfg, rid, allow_existing_run=True: rid)

    rc = entry.run_audio_reroll_preflight(
        rubric_path="/tmp/audio-review-rubric-reviewed.json",
        run_id="reroll-456",
        concept_text="explicit override concept",
        scope="run",
    )
    out = capsys.readouterr().out

    assert rc == 0
    assert seen["concept_text"] == "explicit override concept"
    assert "run_id=reroll-456" in out
