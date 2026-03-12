import pytest

import ai_mv.infra.comfy_transport as ct


def test_wait_history_times_out(monkeypatch):
    monkeypatch.setattr(ct, "_get_json", lambda *_args, **_kwargs: {})
    with pytest.raises(TimeoutError):
        ct.wait_history("http://127.0.0.1:8188", "pid", timeout=1)


def test_wait_history_uses_subsecond_remaining(monkeypatch):
    seen = {"timeout": None}
    ticks = iter([0.0, 0.6, 1.2, 1.8])
    monkeypatch.setattr(ct.time, "time", lambda: next(ticks))
    monkeypatch.setattr(ct.time, "sleep", lambda _x: None)

    def _fake_get_json(_url, timeout):
        seen["timeout"] = timeout
        return {}

    monkeypatch.setattr(ct, "_get_json", _fake_get_json)
    with pytest.raises(TimeoutError):
        ct.wait_history("http://127.0.0.1:8188", "pid", timeout=1)
    assert seen["timeout"] < 1.0


def test_wait_history_wraps_request_error(monkeypatch):
    monkeypatch.setattr(ct, "_get_json", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("boom")))
    with pytest.raises(ct.ComfyRequestError, match="history request failed"):
        ct.wait_history("http://127.0.0.1:8188", "pid", timeout=1)


def test_extract_files_requires_outputs():
    with pytest.raises(ct.ComfyRequestError, match="outputs missing"):
        ct.extract_files({})


def test_submit_workflow_returns_prompt_id_history_and_files(monkeypatch):
    monkeypatch.setattr(ct, "_queue_prompt", lambda *_args, **_kwargs: {"prompt_id": "pid"})
    monkeypatch.setattr(
        ct,
        "wait_history",
        lambda *_args, **_kwargs: {"outputs": {"9": {"images": [{"filename": "x.png"}]}}},
    )
    out = ct.submit_workflow("http://127.0.0.1:8188", {"wf": True}, timeout=3)
    assert out["prompt_id"] == "pid"
    assert out["files"] == ["x.png"]


def test_submit_workflow_raises_execution_error(monkeypatch):
    monkeypatch.setattr(ct, "_queue_prompt", lambda *_args, **_kwargs: {"prompt_id": "pid"})
    monkeypatch.setattr(
        ct,
        "wait_history",
        lambda *_args, **_kwargs: {
            "status": {
                "status_str": "error",
                "messages": [["execution_error", {"node_id": "9", "node_type": "Sampler", "exception_message": "boom"}]],
            },
            "outputs": {"9": {"images": [{"filename": "x.png"}]}},
        },
    )
    with pytest.raises(ct.ComfyRequestError, match="execution_error"):
        ct.submit_workflow("http://127.0.0.1:8188", {"wf": True}, timeout=3)
