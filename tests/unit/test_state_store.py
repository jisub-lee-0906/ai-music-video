import pytest

from ai_mv.core.state import state_store


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

    with pytest.raises(RuntimeError, match="invalid run_id"):
        state_store.read_snapshot("../evil")

    with pytest.raises(RuntimeError, match="invalid run_id"):
        state_store.read_snapshot("abc/def")
