from pathlib import Path
from uuid import uuid4

import pytest

import ai_mv.core.orchestration.preflight as preflight_mod
from ai_mv.core.artifacts.paths import latest_file, latest_success_file, run_file
from ai_mv.core.state.state_store import ensure_run_dir, read_snapshot
from ai_mv.core.state.state_snapshot import save_snapshot


def test_preflight_artifacts_write_to_dedicated_tree():
    path = run_file("test-preflight-artifacts", "prompt_preview.json", scope="preflight")
    latest = latest_file("prompt_preview.json", scope="preflight")
    latest_success = latest_success_file("prompt_preview.json", scope="preflight")
    assert str(path).endswith("artifacts\\preflight\\test-preflight-artifacts\\prompt_preview.json")
    assert str(latest).endswith("artifacts\\preflight\\latest\\prompt_preview.json")
    assert str(latest_success).endswith("artifacts\\preflight\\latest_success\\prompt_preview.json")


def test_preflight_state_uses_dedicated_root(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    run_id = f"pf-state-{uuid4().hex}"
    run_dir = ensure_run_dir(run_id, scope="preflight")
    state = {
        "run_id": run_dir.name,
        "scope": "preflight",
        "status": "running",
        "current_stage": "visual_story_bible",
        "failure_reason": "",
        "completed_stages": ["acestep_music"],
    }
    save_snapshot(state, {"selected_profile": "demo"})
    snap = read_snapshot(run_id, scope="preflight")
    assert snap["scope"] == "preflight"
    assert snap["current_stage"] == "visual_story_bible"
    assert (run_dir / "snapshot.json").exists()


def test_read_snapshot_auto_finds_preflight_state(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    run_id = f"pf-auto-{uuid4().hex}"
    run_dir = ensure_run_dir(run_id, scope="preflight")
    save_snapshot(
        {
            "run_id": run_dir.name,
            "scope": "preflight",
            "status": "failed",
            "current_stage": "shot_timeline",
            "failure_reason": "shot_timeline: boom",
            "completed_stages": ["acestep_music", "lyrics_timeline", "visual_story_bible"],
        },
        {"selected_profile": "demo"},
    )
    snap = read_snapshot(run_id)
    assert snap["scope"] == "preflight"
    assert snap["failure_reason"] == "shot_timeline: boom"


def test_preflight_failure_writes_partial_artifacts_and_traceback(monkeypatch):
    writes: list[str] = []
    snapshots: list[dict] = []

    def _fake_stage(state, _stage_input, name, _fn):
        state["current_stage"] = name
        raise RuntimeError("boom")

    monkeypatch.setattr(
        preflight_mod,
        "init_run_state",
        lambda _cfg, _run_id, allow_existing=False, scope="preflight": {
            "run_id": "pf-fail",
            "scope": "preflight",
            "status": "running",
            "current_stage": "",
            "failure_reason": "",
            "completed_stages": [],
        },
    )
    monkeypatch.setattr(preflight_mod, "_run_preflight_stage", _fake_stage)
    monkeypatch.setattr(preflight_mod, "save_snapshot", lambda state, _payload: snapshots.append(dict(state)))
    monkeypatch.setattr(preflight_mod, "write_manifest", lambda _state, _payload: writes.append("manifest"))
    monkeypatch.setattr(preflight_mod, "write_summary", lambda _state, _payload: writes.append("summary"))
    monkeypatch.setattr(preflight_mod, "write_prompt_preview", lambda _state, _payload: writes.append("prompt_preview"))
    monkeypatch.setattr(preflight_mod, "write_workflow_inputs_preview", lambda _state, _payload: writes.append("workflow_inputs_preview"))
    monkeypatch.setattr(preflight_mod, "write_quality_review", lambda _state, _review: writes.append("quality_review"))
    monkeypatch.setattr(preflight_mod, "write_run_summary", lambda _state, _summary: writes.append("run_summary"))
    monkeypatch.setattr(preflight_mod, "build_quality_review", lambda _cfg, _payload: {})
    monkeypatch.setattr(preflight_mod, "build_run_summary", lambda state, _payload, _review: {"status": state["status"]})

    with pytest.raises(RuntimeError, match="boom"):
        preflight_mod.run_preflight({"profile": "demo"}, "pf-fail")

    assert snapshots[-1]["status"] == "failed"
    assert snapshots[-1]["failure_reason"] == "acestep_music: boom"
    assert "RuntimeError: boom" in snapshots[-1]["failure_traceback"]
    assert writes == [
        "manifest",
        "summary",
        "prompt_preview",
        "workflow_inputs_preview",
        "quality_review",
        "run_summary",
    ]


def test_preflight_stage_validates_input(monkeypatch):
    calls: list[str] = []

    monkeypatch.setattr(preflight_mod, "validate_stage_input", lambda stage, _payload: calls.append(stage))
    monkeypatch.setattr(preflight_mod, "save_snapshot", lambda _state, _payload: None)
    state = {"current_stage": "", "completed_stages": []}
    stage_input = type("StageInputStub", (), {"payload": {"audio_map": {"x": 1}}})()

    preflight_mod._run_preflight_stage(state, stage_input, "visual_story_bible", lambda _stage_input: None)

    assert calls == ["visual_story_bible"]
