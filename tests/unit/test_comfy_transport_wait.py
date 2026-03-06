import pytest

import ai_mv.infra.comfy_transport as ct


def test_wait_history_times_out(monkeypatch):
    monkeypatch.setattr(ct, "_get_json", lambda *_args, **_kwargs: {})
    with pytest.raises(TimeoutError):
        ct.wait_history("http://127.0.0.1:8188", "pid", timeout=1, attempts=2)
