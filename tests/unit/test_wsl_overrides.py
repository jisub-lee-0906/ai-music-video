from __future__ import annotations

from ai_mv.core.orchestration.wsl_overrides import apply_wsl_runtime_overrides


def test_apply_wsl_runtime_overrides_leaves_non_wsl_config_unchanged(monkeypatch):
    cfg = {
        "integrations": {
            "comfyui_base_url": "http://127.0.0.1:8000",
            "comfyui_input_dir": r"C:\Users\Desktop\Documents\ComfyUI\input",
            "comfyui_output_dir": r"C:\Users\Desktop\Documents\ComfyUI\output",
            "codex_cli_path": "",
        }
    }
    monkeypatch.setattr("ai_mv.core.orchestration.wsl_overrides._is_wsl", lambda: False)

    out = apply_wsl_runtime_overrides(cfg)

    assert out == cfg
    assert out is cfg


def test_apply_wsl_runtime_overrides_rewrites_windows_paths_when_env_present(monkeypatch):
    cfg = {
        "integrations": {
            "comfyui_base_url": "http://127.0.0.1:8000",
            "comfyui_input_dir": r"C:\Users\Desktop\Documents\ComfyUI\input",
            "comfyui_output_dir": r"C:\Users\Desktop\Documents\ComfyUI\output",
            "codex_cli_path": "",
        }
    }
    monkeypatch.setattr("ai_mv.core.orchestration.wsl_overrides._is_wsl", lambda: True)
    monkeypatch.setenv("AI_MV_WSL_GATEWAY_HOST", "172.28.224.1")
    monkeypatch.setenv("AI_MV_COMFY_INPUT_DIR", "/mnt/c/Users/Desktop/Documents/ComfyUI/input")
    monkeypatch.setenv("AI_MV_COMFY_OUTPUT_DIR", "/mnt/c/Users/Desktop/Documents/ComfyUI/output")
    monkeypatch.setenv("AI_MV_CODEX_BIN", "/home/jisub-lee/.hermes/node/bin/codex")

    out = apply_wsl_runtime_overrides(cfg)

    assert out["integrations"]["comfyui_base_url"] == "http://172.28.224.1:8000"
    assert out["integrations"]["comfyui_input_dir"] == "/mnt/c/Users/Desktop/Documents/ComfyUI/input"
    assert out["integrations"]["comfyui_output_dir"] == "/mnt/c/Users/Desktop/Documents/ComfyUI/output"
    assert out["integrations"]["codex_cli_path"] == "/home/jisub-lee/.hermes/node/bin/codex"


def test_apply_wsl_runtime_overrides_preserves_linux_safe_values(monkeypatch):
    cfg = {
        "integrations": {
            "comfyui_base_url": "http://10.0.0.9:8000",
            "comfyui_input_dir": "/mnt/c/custom/input",
            "comfyui_output_dir": "/mnt/c/custom/output",
            "codex_cli_path": "/usr/local/bin/codex",
        }
    }
    monkeypatch.setattr("ai_mv.core.orchestration.wsl_overrides._is_wsl", lambda: True)
    monkeypatch.setenv("AI_MV_WSL_GATEWAY_HOST", "172.28.224.1")
    monkeypatch.setenv("AI_MV_COMFY_INPUT_DIR", "/mnt/c/Users/Desktop/Documents/ComfyUI/input")
    monkeypatch.setenv("AI_MV_COMFY_OUTPUT_DIR", "/mnt/c/Users/Desktop/Documents/ComfyUI/output")
    monkeypatch.setenv("AI_MV_CODEX_BIN", "/home/jisub-lee/.hermes/node/bin/codex")

    out = apply_wsl_runtime_overrides(cfg)

    assert out["integrations"]["comfyui_base_url"] == "http://10.0.0.9:8000"
    assert out["integrations"]["comfyui_input_dir"] == "/mnt/c/custom/input"
    assert out["integrations"]["comfyui_output_dir"] == "/mnt/c/custom/output"
    assert out["integrations"]["codex_cli_path"] == "/usr/local/bin/codex"


def test_apply_wsl_runtime_overrides_enables_smoke_mode(monkeypatch):
    cfg = {
        "audio": {
            "target_duration_min_sec": 150,
            "target_duration_max_sec": 180,
        },
        "planning": {
            "enable_ia2v": True,
            "enable_flf2v": True,
        },
        "integrations": {
            "comfyui_base_url": "http://127.0.0.1:8000",
            "comfyui_input_dir": r"C:\\Users\\Desktop\\Documents\\ComfyUI\\input",
            "comfyui_output_dir": r"C:\\Users\\Desktop\\Documents\\ComfyUI\\output",
            "codex_cli_path": "",
        },
    }
    monkeypatch.setattr("ai_mv.core.orchestration.wsl_overrides._is_wsl", lambda: True)
    monkeypatch.setenv("AI_MV_WSL_GATEWAY_HOST", "172.28.224.1")
    monkeypatch.setenv("AI_MV_COMFY_INPUT_DIR", "/mnt/c/Users/Desktop/Documents/ComfyUI/input")
    monkeypatch.setenv("AI_MV_COMFY_OUTPUT_DIR", "/mnt/c/Users/Desktop/Documents/ComfyUI/output")
    monkeypatch.setenv("AI_MV_CODEX_BIN", "/home/jisub-lee/.hermes/node/bin/codex")
    monkeypatch.setenv("AI_MV_WSL_SMOKE_MODE", "1")
    monkeypatch.setenv("AI_MV_SMOKE_AUDIO_MIN_SEC", "15")
    monkeypatch.setenv("AI_MV_SMOKE_AUDIO_MAX_SEC", "20")

    out = apply_wsl_runtime_overrides(cfg)

    assert out["audio"]["target_duration_min_sec"] == 15
    assert out["audio"]["target_duration_max_sec"] == 20
    assert out["planning"]["enable_ia2v"] is False
    assert out["planning"]["enable_flf2v"] is False
