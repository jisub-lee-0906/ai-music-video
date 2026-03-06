import ai_mv.infra.comfy_client as comfy_client


def test_comfy_retry_attempts_passed(monkeypatch, tmp_path):
    captured = {"attempts": None}
    inp = tmp_path / "input"
    outdir = tmp_path / "output"
    inp.mkdir()
    outdir.mkdir()

    def _fake_submit(_base, _workflow, _timeout, attempts=1):
        captured["attempts"] = attempts
        return {"files": []}

    monkeypatch.setattr(comfy_client, "submit_workflow", _fake_submit)
    cfg = {
        "integrations": {
            "comfyui_base_url": "http://127.0.0.1:8188",
            "comfy_retry_attempts": 2,
            "comfyui_input_dir": str(inp),
            "comfyui_output_dir": str(outdir),
        },
        "limits": {"timeout_seconds": 1},
    }
    out = comfy_client.submit(cfg, {})
    assert out == {"files": []}
    assert captured["attempts"] == 2
