import pytest

import ai_mv.infra.comfy_transport as ct


def test_wait_history_times_out(monkeypatch):
    monkeypatch.setattr(ct, "_get_json", lambda *_args, **_kwargs: {})
    with pytest.raises(TimeoutError):
        ct.wait_history("http://127.0.0.1:8000", "pid", timeout=1)


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
        ct.wait_history("http://127.0.0.1:8000", "pid", timeout=1)
    assert seen["timeout"] < 1.0


def test_wait_history_uses_bounded_request_timeout_even_when_total_timeout_disabled(monkeypatch):
    seen = {"timeout": None}

    def _fake_get_json(_url, timeout):
        seen["timeout"] = timeout
        return {"pid": {"outputs": {"9": {"images": [{"filename": "x.png"}]}}}}

    monkeypatch.setattr(ct, "_get_json", _fake_get_json)

    history = ct.wait_history("http://127.0.0.1:8000", "pid", timeout=None)

    assert history["outputs"]
    assert seen["timeout"] == 10.0


def test_wait_history_wraps_request_error(monkeypatch):
    monkeypatch.setattr(ct, "_get_json", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("boom")))
    with pytest.raises(ct.ComfyRequestError, match="history request failed"):
        ct.wait_history("http://127.0.0.1:8000", "pid", timeout=1)


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
    out = ct.submit_workflow("http://127.0.0.1:8000", {"wf": True}, timeout=3)
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
        ct.submit_workflow("http://127.0.0.1:8000", {"wf": True}, timeout=3)


def test_collect_file_entries_ignores_none_subfolder():
    files = ct.extract_files(
        {
            "outputs": {
                "9": {"images": [{"filename": "x.png", "subfolder": None}]},
            }
        }
    )
    assert files == ["x.png"]


def test_free_memory_posts_comfy_free_payload(monkeypatch):
    calls = []

    class _Response:
        status_code = 200

        def raise_for_status(self):
            return None

    def _fake_post(url, json, timeout, allow_redirects):
        calls.append((url, json, timeout, allow_redirects))
        return _Response()

    monkeypatch.setattr(ct.requests, "post", _fake_post)

    ct.free_memory("http://127.0.0.1:8000")

    assert calls == [
        (
            "http://127.0.0.1:8000/free",
            {"unload_models": True, "free_memory": True},
            5,
            False,
        )
    ]


def test_queue_state_disables_and_rejects_redirects(monkeypatch):
    class _Response:
        status_code = 302

    seen = {}

    def _fake_get(url, timeout, allow_redirects):
        seen.update(url=url, timeout=timeout, allow_redirects=allow_redirects)
        return _Response()

    monkeypatch.setattr(ct.requests, "get", _fake_get)
    with pytest.raises(ct.ComfyRequestError, match="redirect is not allowed"):
        ct.queue_state("http://127.0.0.1:8000")
    assert seen["allow_redirects"] is False
