import ai_mv.entrypoints.start as entry
from pathlib import Path


def test_run_start_entry_reports_done(monkeypatch, capsys):
    monkeypatch.setattr(entry, "acquire_lock", lambda _name: object())
    monkeypatch.setattr(entry, "release_lock", lambda _lock: None)
    monkeypatch.setattr(entry, "_load_prepared_config", lambda concept_text: {"concept_text": concept_text or "city pop night drive"})
    monkeypatch.setattr(entry, "run_doctor", lambda _cfg: 0)
    monkeypatch.setattr(entry, "_prepare_comfy_queue", lambda _cfg: None)
    monkeypatch.setattr(entry, "_prepare_run_brief", lambda _cfg, _run_id: "run-123")
    monkeypatch.setattr(entry, "run_pipeline", lambda _cfg, _rid, allow_existing_run=True: "run-123")
    monkeypatch.setattr(
        entry,
        "read_snapshot",
        lambda _rid: {"status": "done", "failure_reason": ""},
    )

    rc = entry.run_start(concept_text="city pop night drive")
    out = capsys.readouterr().out

    assert rc == 0
    assert "run_id=run-123" in out
    assert "status=done" in out


def test_prepare_comfy_queue_interrupts_and_clears(monkeypatch):
    calls: list[tuple[str, str]] = []
    monkeypatch.setattr(entry, "interrupt_comfy", lambda url: calls.append(("interrupt", url)))
    monkeypatch.setattr(entry, "clear_comfy_queue", lambda url: calls.append(("clear", url)))
    monkeypatch.setattr(entry, "comfy_queue_counts", lambda url: (0, 0))
    cfg = {
        "integrations": {"comfyui_base_url": "http://127.0.0.1:8000"},
        "runtime": {"interrupt_comfy_before_start": True, "clear_comfy_queue_before_start": True},
    }
    entry._prepare_comfy_queue(cfg)
    assert calls == [("interrupt", "http://127.0.0.1:8000"), ("clear", "http://127.0.0.1:8000")]


def test_prepare_comfy_queue_raises_when_not_empty(monkeypatch):
    monkeypatch.setattr(entry, "interrupt_comfy", lambda _url: None)
    monkeypatch.setattr(entry, "clear_comfy_queue", lambda _url: None)
    monkeypatch.setattr(entry, "comfy_queue_counts", lambda _url: (1, 2))
    cfg = {
        "integrations": {"comfyui_base_url": "http://127.0.0.1:8000"},
        "runtime": {"interrupt_comfy_before_start": True, "clear_comfy_queue_before_start": True},
    }
    try:
        entry._prepare_comfy_queue(cfg)
        raised = False
    except RuntimeError as exc:
        raised = True
        assert "queue is not empty" in str(exc)
    assert raised


def test_prepare_run_brief_writes_concept_text_to_state_and_artifacts(monkeypatch, tmp_path):
    state_dir = tmp_path / "runs_state" / "run-123"
    artifact_file = tmp_path / "runs" / "run-123" / "inputs" / "concept_text.txt"
    state_dir.mkdir(parents=True)
    monkeypatch.setattr(entry, "ensure_run_dir", lambda _run_id, allow_existing=False: state_dir)
    monkeypatch.setattr(entry, "run_file", lambda run_id, name: tmp_path / "runs" / run_id / Path(name))
    rid = entry._prepare_run_brief({"concept_text": "city pop night drive"}, "run-123")
    assert rid == "run-123"
    assert (state_dir / "concept_text.txt").read_text(encoding="utf-8") == "city pop night drive"
    assert artifact_file.read_text(encoding="utf-8") == "city pop night drive"


def test_prepare_run_brief_does_not_write_audio_specific_briefs(monkeypatch, tmp_path):
    state_dir = tmp_path / "runs_state" / "run-123"
    state_dir.mkdir(parents=True)
    monkeypatch.setattr(entry, "ensure_run_dir", lambda _run_id, allow_existing=False: state_dir)
    monkeypatch.setattr(entry, "run_file", lambda run_id, name: tmp_path / "runs" / run_id / Path(name))
    rid = entry._prepare_run_brief(
        {
            "concept_text": "shared concept",
            "audio": {"brief": "music-facing brief", "hook_brief": "title-grade hook"},
        },
        "run-123",
    )
    assert rid == "run-123"
    assert not (state_dir / "audio_brief.txt").exists()
    assert not (state_dir / "audio_hook_brief.txt").exists()
    assert not (tmp_path / "runs" / "run-123" / "inputs" / "audio_brief.txt").exists()
    assert not (tmp_path / "runs" / "run-123" / "inputs" / "audio_hook_brief.txt").exists()
