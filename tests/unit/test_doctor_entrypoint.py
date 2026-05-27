import ai_mv.entrypoints.doctor as doctor


def test_run_doctor_uses_same_config_for_ping_and_assert(monkeypatch):
    cfg = {
        "integrations": {
            "comfyui_base_url": "http://127.0.0.1:8000",
            "codex_cli_path": "C:/tools/codex.cmd",
        }
    }
    seen = {}

    monkeypatch.setattr(doctor, "apply_runtime_overrides", lambda passed_cfg: passed_cfg)
    monkeypatch.setattr(doctor, "assert_runtime_ready", lambda _cfg: None)
    monkeypatch.setattr(doctor, "assert_codex_ready", lambda _cfg: None)
    monkeypatch.setattr(doctor, "ping_comfy", lambda _url: True)

    def _fake_ping_codex(passed_cfg):
        seen["config"] = passed_cfg
        return True

    monkeypatch.setattr(doctor, "ping_codex", _fake_ping_codex)

    assert doctor.run_doctor(cfg) == 0
    assert seen["config"] == cfg


def test_run_doctor_applies_wsl_runtime_overrides(monkeypatch):
    seen = {}
    cfg = {"integrations": {"comfyui_base_url": "http://127.0.0.1:8000"}}

    def _fake_apply(passed_cfg):
        seen["before"] = passed_cfg
        return {"integrations": {"comfyui_base_url": "http://127.0.0.1:8000", "codex_cli_path": "C:/tools/codex.cmd"}}

    monkeypatch.setattr(doctor, "apply_runtime_overrides", _fake_apply)
    monkeypatch.setattr(doctor, "assert_runtime_ready", lambda _cfg: None)
    monkeypatch.setattr(doctor, "assert_codex_ready", lambda _cfg: None)
    monkeypatch.setattr(doctor, "ping_comfy", lambda _url: True)
    monkeypatch.setattr(doctor, "ping_codex", lambda passed_cfg: passed_cfg["integrations"]["codex_cli_path"] == "C:/tools/codex.cmd")

    assert doctor.run_doctor(cfg) == 0
    assert seen["before"] == cfg
