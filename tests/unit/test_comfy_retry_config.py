import ai_mv.infra.comfy_client as comfy_client


def test_comfy_retry_attempts_passed(monkeypatch):
    captured = {"attempts": None}

    def _fake_submit(_base, _workflow, _timeout, attempts=1):
        captured["attempts"] = attempts
        return {"files": []}

    monkeypatch.setattr(comfy_client, "submit_workflow", _fake_submit)
    cfg = {
        "integrations": {"comfyui_base_url": "http://127.0.0.1:8188", "comfy_retry_attempts": 2},
        "limits": {"timeout_seconds": 1},
    }
    out = comfy_client.submit(cfg, {})
    assert out == {"files": []}
    assert captured["attempts"] == 2
