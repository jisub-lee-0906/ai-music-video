import pytest

import ai_mv.infra.comfy_transport as ct


def test_wait_history_times_out(monkeypatch):
    monkeypatch.setattr(ct, "_get_json", lambda *_args, **_kwargs: {})
    with pytest.raises(TimeoutError):
        ct.wait_history("http://127.0.0.1:8188", "pid", timeout=1, attempts=2)


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
        ct.wait_history("http://127.0.0.1:8188", "pid", timeout=1, attempts=1)
    assert seen["timeout"] < 1.0


def test_queue_with_deadline_uses_remaining(monkeypatch):
    seen = {"timeout": None}
    ticks = iter([0.0, 0.4, 0.9, 1.2])
    monkeypatch.setattr(ct.time, "time", lambda: next(ticks))

    def _fake_queue(_base, _wf, timeout):
        seen["timeout"] = timeout
        raise RuntimeError("queue fail")

    monkeypatch.setattr(ct, "_queue_prompt", _fake_queue)
    with pytest.raises(RuntimeError):
        ct._queue_with_deadline("http://127.0.0.1:8188", {}, timeout=1, attempts=3)
    assert seen["timeout"] < 1.0


def test_queue_with_deadline_no_retry_for_4xx(monkeypatch):
    calls = {"n": 0}

    def _fake_queue(_base, _wf, _timeout):
        calls["n"] += 1
        raise ct.ComfyRequestError("Comfy prompt failed: 400 bad request")

    monkeypatch.setattr(ct, "_queue_prompt", _fake_queue)
    with pytest.raises(ct.ComfyRequestError):
        ct._queue_with_deadline("http://127.0.0.1:8188", {}, timeout=2, attempts=5)
    assert calls["n"] == 1


def test_wait_history_wraps_request_error(monkeypatch):
    monkeypatch.setattr(ct, "_get_json", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("boom")))
    with pytest.raises(ct.ComfyRequestError, match="history request failed"):
        ct.wait_history("http://127.0.0.1:8188", "pid", timeout=1, attempts=1)


def test_wait_history_retries_request_error(monkeypatch):
    calls = {"n": 0}

    def _fake_get_json(_url, _timeout):
        calls["n"] += 1
        if calls["n"] < 2:
            raise RuntimeError("boom")
        return {"pid": {"outputs": {"9": {"images": [{"filename": "x.png"}]}}}}

    monkeypatch.setattr(ct, "_get_json", _fake_get_json)
    out = ct.wait_history("http://127.0.0.1:8188", "pid", timeout=1, attempts=2)
    assert "outputs" in out
    assert calls["n"] == 2


def test_history_attempt_timeout_splits_remaining_budget():
    assert ct._history_attempt_timeout(1.2, 3) == pytest.approx(0.4)
    assert ct._history_attempt_timeout(0.01, 3) == pytest.approx(0.05)


def test_extract_files_requires_outputs():
    with pytest.raises(ct.ComfyRequestError, match="outputs missing"):
        ct.extract_files({})
