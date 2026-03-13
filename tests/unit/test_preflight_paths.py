from pathlib import Path
from uuid import uuid4

from ai_mv.core.artifacts.paths import latest_file, run_file
from ai_mv.core.state.state_store import ensure_run_dir, read_snapshot
from ai_mv.core.state.state_snapshot import save_snapshot


def test_preflight_artifacts_write_to_dedicated_tree():
    path = run_file("test-preflight-artifacts", "prompt_preview.json", scope="preflight")
    latest = latest_file("prompt_preview.json", scope="preflight")
    assert str(path).endswith("artifacts\\preflight\\test-preflight-artifacts\\prompt_preview.json")
    assert str(latest).endswith("artifacts\\preflight\\latest\\prompt_preview.json")


def test_preflight_state_uses_dedicated_root(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    run_id = f"pf-state-{uuid4().hex}"
    run_dir = ensure_run_dir(run_id, scope="preflight")
    state = {
        "run_id": run_dir.name,
        "scope": "preflight",
        "status": "running",
        "current_stage": "visual_bridge",
        "failure_reason": "",
        "completed_stages": ["acestep_music"],
    }
    save_snapshot(state, {"selected_profile": "demo"})
    snap = read_snapshot(run_id, scope="preflight")
    assert snap["scope"] == "preflight"
    assert snap["current_stage"] == "visual_bridge"
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
            "current_stage": "tti_anchor",
            "failure_reason": "tti_anchor: boom",
            "completed_stages": ["acestep_music", "visual_bridge"],
        },
        {"selected_profile": "demo"},
    )
    snap = read_snapshot(run_id)
    assert snap["scope"] == "preflight"
    assert snap["failure_reason"] == "tti_anchor: boom"
