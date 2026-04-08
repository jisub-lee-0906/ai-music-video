import pytest

from ai_mv.core.state import state_store
from ai_mv.core.artifacts import paths as artifact_paths


def test_ensure_run_dir_rejects_path_traversal(monkeypatch, tmp_path):
    monkeypatch.setattr(state_store, "PROJECT_ROOT", tmp_path)

    with pytest.raises(RuntimeError, match="invalid run_id"):
        state_store.ensure_run_dir("../evil", scope="run")

    with pytest.raises(RuntimeError, match="invalid run_id"):
        state_store.ensure_run_dir("abc/def", scope="run")

    with pytest.raises(RuntimeError, match="invalid run_id"):
        state_store.ensure_run_dir("..\\evil", scope="run")


def test_read_snapshot_rejects_path_traversal(tmp_path, monkeypatch):
    monkeypatch.setattr(state_store, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(artifact_paths, "PROJECT_ROOT", tmp_path)

    with pytest.raises(RuntimeError, match="invalid run_id"):
        state_store.read_snapshot("../evil")

    with pytest.raises(RuntimeError, match="invalid run_id"):
        state_store.read_snapshot("abc/def")


def test_ensure_run_dir_creates_matching_artifact_root(monkeypatch, tmp_path):
    monkeypatch.setattr(state_store, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(artifact_paths, "PROJECT_ROOT", tmp_path)
    run_dir = state_store.ensure_run_dir("run-123", scope="run")
    assert run_dir == tmp_path / "artifacts" / "runs_state" / "run-123"
    assert (tmp_path / "artifacts" / "runs" / "run-123").is_dir()


def test_read_snapshot_prefers_artifact_snapshot_when_present(monkeypatch, tmp_path):
    monkeypatch.setattr(state_store, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(artifact_paths, "PROJECT_ROOT", tmp_path)
    snap = tmp_path / "artifacts" / "runs" / "run-123" / "snapshot.json"
    snap.parent.mkdir(parents=True)
    snap.write_text('{\"run_id\":\"run-123\",\"scope\":\"run\",\"status\":\"done\",\"current_stage\":\"review\",\"failure_reason\":\"\",\"completed_stages\":[\"audio\"]}', encoding="utf-8")
    out = state_store.read_snapshot("run-123", scope="run")
    assert out["status"] == "done"
    assert out["current_stage"] == "review"
